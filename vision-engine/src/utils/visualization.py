"""Drawing utilities for detections, zones, and tracks."""

import cv2
import numpy as np


COLORS = {
    "restricted": (0, 0, 255),    # Red
    "monitored": (0, 255, 255),   # Yellow
    "required_presence": (0, 255, 0),  # Green
    "default": (255, 128, 0),     # Orange
}


def draw_detections(
    frame: np.ndarray,
    detections: list[dict],
    color: tuple[int, int, int] = (0, 255, 0),
    thickness: int = 2,
) -> np.ndarray:
    """Draw bounding boxes and labels on a frame."""
    annotated = frame.copy()
    for det in detections:
        bbox = det["bbox"]
        x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        conf = det.get("confidence", 0)
        track_id = det.get("track_id", -1)

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)

        label = f"Person {conf:.2f}"
        if track_id >= 0:
            label = f"ID:{track_id} {conf:.2f}"

        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)
        cv2.putText(annotated, label, (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    return annotated


def draw_zones(
    frame: np.ndarray,
    zones: list[dict],
    alpha: float = 0.3,
) -> np.ndarray:
    """Draw zone polygons on a frame.

    Args:
        zones: List of {"polygon_points": [...], "zone_type": str, "name": str}
    """
    overlay = frame.copy()
    h, w = frame.shape[:2]

    for zone in zones:
        zone_type = zone.get("zone_type", "default")
        color = COLORS.get(zone_type, COLORS["default"])
        points = zone.get("polygon_points", [])

        pts = np.array([[int(p["x"] * w), int(p["y"] * h)] for p in points], dtype=np.int32)

        if len(pts) >= 3:
            cv2.fillPoly(overlay, [pts], color)
            cv2.polylines(frame, [pts], True, color, 2)

            name = zone.get("name", "")
            if name and len(pts) > 0:
                cx = int(np.mean(pts[:, 0]))
                cy = int(np.mean(pts[:, 1]))
                cv2.putText(frame, name, (cx - 20, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
