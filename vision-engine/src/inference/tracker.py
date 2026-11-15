"""ByteTrack-based multi-object tracker using supervision library."""

import logging

import numpy as np

from src.inference.detector import Detection

logger = logging.getLogger("saferest360.tracker")


class PersonTracker:
    """Track detected persons across frames using ByteTrack."""

    def __init__(
        self,
        track_activation_threshold: float = 0.25,
        lost_track_buffer: int = 30,
        minimum_matching_threshold: float = 0.8,
        frame_rate: int = 15,
    ):
        try:
            import supervision as sv
            self._tracker = sv.ByteTrack(
                track_activation_threshold=track_activation_threshold,
                lost_track_buffer=lost_track_buffer,
                minimum_matching_threshold=minimum_matching_threshold,
                frame_rate=frame_rate,
            )
            self._sv = sv
            self._available = True
        except (ImportError, AttributeError):
            # supervision>=0.31 removed ByteTrack; requirements pin <0.31
            logger.warning("ByteTrack no disponible (instala supervision<0.31); IDs de seguimiento no persistentes")
            self._tracker = None
            self._available = False
            self._next_id = 0
            self._simple_tracks: dict[int, list[float]] = {}

    def update(self, detections: list[Detection]) -> list[Detection]:
        """Update tracker with new detections and return tracked detections.

        Each returned Detection will have a track_id assigned.
        """
        if not detections:
            return []

        if self._available:
            return self._update_supervision(detections)
        return self._update_simple(detections)

    def _update_supervision(self, detections: list[Detection]) -> list[Detection]:
        sv = self._sv
        xyxy = np.array([d.bbox for d in detections], dtype=np.float32)
        confidence = np.array([d.confidence for d in detections], dtype=np.float32)
        class_id = np.array([d.class_id for d in detections], dtype=int)

        sv_detections = sv.Detections(
            xyxy=xyxy,
            confidence=confidence,
            class_id=class_id,
        )

        tracked = self._tracker.update_with_detections(sv_detections)

        results = []
        for i in range(len(tracked)):
            d = Detection(
                bbox=tracked.xyxy[i].tolist(),
                confidence=float(tracked.confidence[i]) if tracked.confidence is not None else 0.0,
                class_id=int(tracked.class_id[i]) if tracked.class_id is not None else 0,
                track_id=int(tracked.tracker_id[i]) if tracked.tracker_id is not None else -1,
            )
            results.append(d)

        return results

    def _update_simple(self, detections: list[Detection]) -> list[Detection]:
        """Fallback naive tracker: assign sequential IDs."""
        results = []
        for d in detections:
            d.track_id = self._next_id
            self._next_id += 1
            results.append(d)
        return results

    def reset(self):
        if self._available:
            self._tracker.reset()
        else:
            self._next_id = 0
            self._simple_tracks.clear()
