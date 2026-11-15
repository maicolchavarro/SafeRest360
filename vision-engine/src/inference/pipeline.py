"""Full frame processing pipeline: detect → track → zone check → rules → events."""

import time
from datetime import datetime

import numpy as np

from src.inference.detector import Detector
from src.inference.tracker import PersonTracker
from src.rules.engine import RulesEngine
from src.rules.events import Event


class VisionPipeline:
    """Complete vision processing pipeline for a single camera.

    Pipeline: frame → YOLO detector → ByteTrack → zone check → rules → events
    """

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        device: str = "cpu",
        confidence: float = 0.5,
        frame_rate: int = 15,
    ):
        self._detector = Detector(model_path, device, confidence)
        self._tracker = PersonTracker(frame_rate=frame_rate)
        self._rules_engine = RulesEngine()
        self._confidence = confidence

    @property
    def rules_engine(self) -> RulesEngine:
        return self._rules_engine

    def process_frame(
        self,
        frame: np.ndarray,
        confidence: float | None = None,
        local_time: datetime | None = None,
    ) -> dict:
        """Process a single frame through the full pipeline.

        Args:
            frame: BGR numpy array (H, W, C)
            confidence: Override default confidence threshold
            local_time: Wall-clock time in the restaurant's timezone (for rule schedules)

        Returns:
            Dict with detections, tracked_persons, events, rule_states and metadata
        """
        h, w = frame.shape[:2]

        raw_detections = self._detector.detect_raw(frame, confidence or self._confidence)

        tracked = self._tracker.update(raw_detections)
        tracked_dicts = [d.to_dict() for d in tracked]

        now = time.time()
        events = self._rules_engine.evaluate(tracked_dicts, w, h, current_time=now, local_time=local_time)

        return {
            "frame_size": {"width": w, "height": h},
            "detections_count": len(raw_detections),
            "tracked_persons": tracked_dicts,
            "events": [e.to_dict() for e in events],
            "rule_states": self._rules_engine.get_states(now),
        }

    def reset_tracker(self):
        self._tracker.reset()


def process_video(
    video_path: str,
    pipeline: VisionPipeline,
    max_frames: int | None = None,
    skip_frames: int = 1,
) -> list[dict]:
    """Process a video file through the pipeline.

    Args:
        video_path: Path to video file
        pipeline: Configured VisionPipeline
        max_frames: Maximum frames to process
        skip_frames: Process every Nth frame

    Returns:
        List of frame results
    """
    import cv2

    cap = cv2.VideoCapture(video_path)
    results = []
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % skip_frames == 0:
            result = pipeline.process_frame(frame)
            result["frame_index"] = frame_idx
            results.append(result)

        frame_idx += 1
        if max_frames and frame_idx >= max_frames:
            break

    cap.release()
    return results
