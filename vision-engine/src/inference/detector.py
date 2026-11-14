"""Person detector using YOLO models."""

from pathlib import Path
from typing import ClassVar

import numpy as np


class Detection:
    """Single detection result."""

    __slots__ = ("bbox", "confidence", "class_id", "track_id")

    def __init__(self, bbox: list[float], confidence: float, class_id: int = 0, track_id: int = -1):
        self.bbox = bbox  # [x1, y1, x2, y2] in pixels
        self.confidence = confidence
        self.class_id = class_id
        self.track_id = track_id

    def to_dict(self) -> dict:
        return {
            "bbox": self.bbox,
            "confidence": round(self.confidence, 4),
            "class_id": self.class_id,
            "track_id": self.track_id,
        }

    @property
    def center(self) -> tuple[float, float]:
        return ((self.bbox[0] + self.bbox[2]) / 2, (self.bbox[1] + self.bbox[3]) / 2)


class Detector:
    """YOLO-based person detector with singleton pattern for model reuse."""

    _instance: ClassVar["Detector | None"] = None
    _model = None
    _model_path: str = ""

    def __init__(self, model_path: str, device: str = "cpu", confidence: float = 0.5):
        self._model_path = model_path
        self._device = device
        self._default_confidence = confidence
        self._load_model()

    def _load_model(self):
        from ultralytics import YOLO
        self._model = YOLO(self._model_path)

    @classmethod
    def get_instance(cls, model_path: str = "", device: str = "cpu", confidence: float = 0.5) -> "Detector":
        if cls._instance is None or (model_path and model_path != cls._model_path):
            cls._instance = cls(model_path or "yolov8n.pt", device, confidence)
        return cls._instance

    def detect(
        self,
        frame: np.ndarray,
        confidence_threshold: float | None = None,
    ) -> list[dict]:
        """Run person detection on a frame.

        Args:
            frame: BGR or RGB numpy array (H, W, C)
            confidence_threshold: Min confidence to keep a detection

        Returns:
            List of detection dicts with bbox, confidence, class_id
        """
        conf = confidence_threshold or self._default_confidence

        results = self._model(frame, conf=conf, device=self._device, verbose=False)

        detections = []
        for r in results:
            boxes = r.boxes
            if boxes is None:
                continue
            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i].item())
                # COCO class 0 = person; single_cls models always use 0
                if cls_id == 0:
                    xyxy = boxes.xyxy[i].cpu().numpy().tolist()
                    conf_val = float(boxes.conf[i].item())
                    detections.append(Detection(xyxy, conf_val, cls_id).to_dict())

        return detections

    def detect_raw(
        self,
        frame: np.ndarray,
        confidence_threshold: float | None = None,
    ) -> list[Detection]:
        """Return Detection objects (for tracker integration)."""
        conf = confidence_threshold or self._default_confidence
        results = self._model(frame, conf=conf, device=self._device, verbose=False)

        detections = []
        for r in results:
            boxes = r.boxes
            if boxes is None:
                continue
            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i].item())
                if cls_id == 0:
                    xyxy = boxes.xyxy[i].cpu().numpy().tolist()
                    conf_val = float(boxes.conf[i].item())
                    detections.append(Detection(xyxy, conf_val, cls_id))

        return detections
