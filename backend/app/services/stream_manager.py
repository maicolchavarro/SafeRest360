"""Live camera processing: one worker per RTSP camera feeds the vision pipeline and turns rule events into alerts.

Runs inside the API process for the local demo. In production this belongs in camera-connector, on the
restaurant's network, so cameras are never exposed to the internet (Brief section D). Frames only live in
memory; an image is written to disk only when an alert fires.
"""

import asyncio
import logging
import os
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import cv2
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models import Alert, Camera, Notification, Restaurant, Rule, User, Zone
from app.services import inference_service  # noqa: F401  (puts vision-engine on sys.path)
from app.services.whatsapp_client import send_alert_notification as send_whatsapp
from app.services.telegram_client import send_alert_notification as send_telegram, TelegramDeliveryError

logger = logging.getLogger("saferest360.streams")

os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

ENGINE_RULE_TYPES = {
    "no_entry": "no_entry",
    "zone_abandoned": "zone_abandoned",
    "required_presence": "zone_abandoned",
    "max_occupancy": "max_occupancy",
}
STALE_AFTER_SECONDS = 10


@dataclass
class PendingAlert:
    camera_id: uuid.UUID
    rule_id: uuid.UUID
    zone_id: uuid.UUID
    event: dict
    snapshot_jpeg: bytes


class CameraWorker:
    """Reads one stream in a thread (keeping only the newest frame) and analyses it in another."""

    def __init__(self, camera_id: uuid.UUID, source: str, analysis_fps: float, on_event, timezone_name: str = "UTC"):
        self.camera_id = camera_id
        self.source = source
        self._tz = ZoneInfo(timezone_name)
        self.rule_states: list[dict] = []
        self._interval = 1.0 / analysis_fps
        self._on_event = on_event
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._frame = None
        self._frame_seq = 0
        self._zones: list[dict] = []
        self._rules_signature = None
        self._pending_rules = None
        self.error: str | None = None
        self.latest_jpeg: bytes | None = None
        self.persons_in_view = 0
        self.analysis_fps = 0.0
        self.last_frame_at: datetime | None = None
        self._threads = [
            threading.Thread(target=self._read_loop, name=f"cam-read-{camera_id}", daemon=True),
            threading.Thread(target=self._analyze_loop, name=f"cam-analyze-{camera_id}", daemon=True),
        ]

    def start(self) -> None:
        for t in self._threads:
            t.start()

    def stop(self) -> None:
        self._stop.set()

    @property
    def status(self) -> str:
        if self.last_frame_at and (datetime.now(timezone.utc) - self.last_frame_at).total_seconds() < STALE_AFTER_SECONDS:
            return "online"
        return "error" if self.error and self.error.startswith("Modelo") else "offline"

    def set_rules(self, zones: list[dict], rules: list[dict]) -> None:
        signature = repr((zones, rules))
        if signature == self._rules_signature:
            return
        self._rules_signature = signature
        with self._lock:
            self._pending_rules = (zones, rules)

    def _read_loop(self) -> None:
        backoff = 2.0
        while not self._stop.is_set():
            cap = cv2.VideoCapture(
                self.source, cv2.CAP_FFMPEG,
                [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 8000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 8000],
            )
            if not cap.isOpened():
                cap.release()
                self.error = "No se pudo abrir el stream"
                self._stop.wait(backoff)
                backoff = min(backoff * 2, 30.0)
                continue
            backoff = 2.0
            self.error = None
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    break
                with self._lock:
                    self._frame = frame
                    self._frame_seq += 1
                self.last_frame_at = datetime.now(timezone.utc)
            cap.release()
            if not self._stop.is_set():
                self.error = "Se perdió la conexión con la cámara"
                self._stop.wait(backoff)

    def _apply_rules(self, pipeline, pending) -> None:
        from src.rules.engine import RuleConfig
        from src.rules.zone import ZonePolygon

        zones, rules = pending
        by_id = {z["id"]: z for z in zones}
        configs = []
        for r in rules:
            z = by_id.get(r["zone_id"])
            rule_type = ENGINE_RULE_TYPES.get(r["rule_type"])
            if z is None or rule_type is None:
                continue
            configs.append(RuleConfig(
                rule_id=r["id"],
                rule_type=rule_type,
                zone=ZonePolygon(z["id"], z["name"], z["zone_type"], z["polygon_points"], z["color"]),
                camera_id=str(self.camera_id),
                parameters=r["parameters"] or {},
                severity=r["severity"],
                cooldown_seconds=r["cooldown_seconds"],
                schedule=r.get("schedule"),
            ))
        pipeline.rules_engine.set_rules(configs)
        self._zones = zones

    def _analyze_loop(self) -> None:
        try:
            from src.inference.pipeline import VisionPipeline
            from src.utils.visualization import draw_detections

            pipeline = VisionPipeline(
                model_path=settings.VISION_MODEL_PATH,
                device=settings.VISION_DEVICE,
                confidence=settings.VISION_CONFIDENCE_THRESHOLD,
                frame_rate=max(1, round(1 / self._interval)),
            )
        except Exception as exc:  # model download/load problems should show on the camera, not kill the API
            logger.exception("No se pudo cargar el modelo para la cámara %s", self.camera_id)
            self.error = f"Modelo no disponible: {exc}"
            return

        done = deque(maxlen=20)
        last_seq = 0
        while not self._stop.is_set():
            with self._lock:
                pending, self._pending_rules = self._pending_rules, None
                frame, seq = self._frame, self._frame_seq
            if pending is not None:
                self._apply_rules(pipeline, pending)
            if frame is None or seq == last_seq:
                self._stop.wait(0.05)
                continue
            last_seq = seq
            started = time.monotonic()
            try:
                result = pipeline.process_frame(frame, local_time=datetime.now(self._tz))
                self.rule_states = result["rule_states"]
                persons = result["tracked_persons"]
                annotated = draw_detections(frame, persons)
                self.latest_jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])[1].tobytes()
                self.persons_in_view = len(persons)
                if result["events"]:
                    for event in result["events"]:
                        offenders = event.get("detection_data") or persons
                        snapshot = draw_detections(frame.copy(), offenders, color=(0, 0, 255), thickness=2)
                        snapshot_jpeg = cv2.imencode(".jpg", snapshot, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes()
                        self._on_event(PendingAlert(
                            camera_id=self.camera_id,
                            rule_id=uuid.UUID(event["rule_id"]),
                            zone_id=uuid.UUID(event["zone_id"]),
                            event=event,
                            snapshot_jpeg=snapshot_jpeg,
                        ))
            except Exception:
                logger.exception("Error analizando cuadro de la cámara %s", self.camera_id)
            done.append(time.monotonic())
            if len(done) > 1:
                self.analysis_fps = (len(done) - 1) / (done[-1] - done[0])
            self._stop.wait(max(0.0, self._interval - (time.monotonic() - started)))


class StreamManager:
    def __init__(self) -> None:
        self._workers: dict[uuid.UUID, CameraWorker] = {}
        self._tasks: list[asyncio.Task] = []
        self._queue: asyncio.Queue | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def get(self, camera_id: uuid.UUID) -> CameraWorker | None:
        return self._workers.get(camera_id)

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue(maxsize=200)
        self._tasks = [asyncio.create_task(self._sync_forever()), asyncio.create_task(self._consume_alerts())]

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        for worker in self._workers.values():
            worker.stop()
        self._workers.clear()

    def _enqueue(self, pending: PendingAlert) -> None:
        self._loop.call_soon_threadsafe(self._put, pending)

    def _put(self, pending: PendingAlert) -> None:
        try:
            self._queue.put_nowait(pending)
        except asyncio.QueueFull:
            logger.warning("Cola de alertas llena; se descarta un evento de la cámara %s", pending.camera_id)

    async def _sync_forever(self) -> None:
        while True:
            try:
                await self.sync_once()
            except Exception:
                logger.exception("Error sincronizando cámaras")
            await asyncio.sleep(settings.STREAM_SYNC_SECONDS)

    async def sync_once(self) -> None:
        """Start/stop workers to match the DB, push current zones/rules, and persist camera status."""
        async with async_session() as db:
            cameras = (await db.execute(
                select(Camera).where(Camera.is_active == True, Camera.rtsp_url.is_not(None), Camera.rtsp_url != "")
            )).scalars().all()
            wanted = {c.id: c for c in cameras}

            for cid, worker in list(self._workers.items()):
                if cid not in wanted or worker.source != wanted[cid].rtsp_url:
                    worker.stop()
                    del self._workers[cid]

            for cid, camera in wanted.items():
                worker = self._workers.get(cid)
                if worker is None:
                    restaurant = await db.get(Restaurant, camera.restaurant_id)
                    worker = CameraWorker(cid, camera.rtsp_url, settings.STREAM_ANALYSIS_FPS, self._enqueue,
                                          timezone_name=restaurant.timezone)
                    worker.start()
                    self._workers[cid] = worker
                    logger.info("Leyendo cámara %s (%s)", camera.name, cid)

                zones = (await db.execute(
                    select(Zone).where(Zone.camera_id == cid, Zone.is_active == True)
                )).scalars().all()
                rules = []
                if zones:
                    rules = (await db.execute(
                        select(Rule).where(Rule.zone_id.in_([z.id for z in zones]), Rule.is_active == True)
                    )).scalars().all()
                worker.set_rules(
                    [{"id": str(z.id), "name": z.name, "zone_type": z.zone_type,
                      "polygon_points": z.polygon_points, "color": z.color} for z in zones],
                    [{"id": str(r.id), "zone_id": str(r.zone_id), "rule_type": r.rule_type,
                      "parameters": r.parameters, "severity": r.severity,
                      "cooldown_seconds": r.cooldown_seconds, "schedule": r.schedule} for r in rules],
                )
                camera.status = worker.status
                if worker.last_frame_at:
                    camera.last_heartbeat = worker.last_frame_at
            await db.commit()

    async def _consume_alerts(self) -> None:
        while True:
            pending = await self._queue.get()
            try:
                await self.persist_alert(pending)
            except Exception:
                logger.exception("No se pudo guardar la alerta de la cámara %s", pending.camera_id)

    async def persist_alert(self, pending: PendingAlert) -> Alert | None:
        event = pending.event
        async with async_session() as db:
            camera = await db.get(Camera, pending.camera_id)
            if camera is None:
                return None
            alert = Alert(
                rule_id=pending.rule_id,
                camera_id=camera.id,
                zone_id=pending.zone_id,
                restaurant_id=camera.restaurant_id,
                alert_type=event["event_type"],
                severity=event["severity"],
                description=event["description"],
                detection_data={"persons_detected": event["persons_detected"], "detections": event["detection_data"]},
                triggered_at=datetime.fromisoformat(event["timestamp"]),
            )
            db.add(alert)
            await db.flush()

            path = (Path(settings.SNAPSHOT_LOCAL_PATH) / str(camera.restaurant_id) / f"{alert.id}.jpg").resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(path.write_bytes, pending.snapshot_jpeg)
            alert.snapshot_path = str(path)

            # The alert and snapshot must survive provider failures or process interruption.
            await db.commit()
            channel = settings.NOTIFICATION_CHANNEL
            recipient_field = User.telegram_chat_id if channel == "telegram" else User.phone_whatsapp
            admins = [] if channel == "disabled" else (await db.execute(
                select(User).where(
                    User.restaurant_id == camera.restaurant_id, User.role == "admin",
                    User.is_active == True, recipient_field.is_not(None), recipient_field != "",
                )
            )).scalars().all()
            # One delivery per destination per alert, even when admins share a group.
            recipients_seen = set()
            for admin in admins:
                recipient = admin.telegram_chat_id if channel == "telegram" else admin.phone_whatsapp
                if recipient in recipients_seen:
                    continue
                recipients_seen.add(recipient)
                notification = Notification(alert_id=alert.id, user_id=admin.id, channel=channel)
                db.add(notification)
                await db.commit()
                try:
                    args = (recipient, alert.alert_type, f"{camera.name}: {alert.description}", alert.severity)
                    if channel == "telegram":
                        sent = await send_telegram(
                            *args, token=settings.TELEGRAM_BOT_TOKEN, test_mode=settings.TELEGRAM_TEST_MODE,
                            photo_bytes=pending.snapshot_jpeg,
                        )
                    else:
                        sent = await send_whatsapp(*args)
                    notification.status = sent["status"]
                    notification.external_message_id = sent.get("message_id")
                    if sent["status"] == "sent":
                        notification.sent_at = datetime.now(timezone.utc)
                except TelegramDeliveryError as exc:
                    notification.status = exc.status
                    notification.error_message = str(exc)
                except Exception:
                    # Provider exceptions can contain URLs with credentials.
                    notification.status = "unknown"
                    notification.error_message = "No se pudo confirmar el envío de la notificación."
                    logger.warning("Error de notificación %s; revisar el destino antes de reintentar.", notification.id)
                await db.commit()

            await db.refresh(alert)
            logger.info("Alerta %s (%s) en cámara %s", alert.alert_type, alert.severity, camera.name)
            return alert


stream_manager = StreamManager()
