"""Geometric utilities for zone detection."""


def point_in_polygon(point: tuple[float, float], polygon: list[dict]) -> bool:
    """Check if a point is inside a polygon using ray-casting algorithm.

    Args:
        point: (x, y) coordinates
        polygon: List of {"x": float, "y": float} dicts defining the polygon vertices

    Returns:
        True if the point is inside the polygon
    """
    x, y = point
    n = len(polygon)
    inside = False

    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]["x"], polygon[i]["y"]
        xj, yj = polygon[j]["x"], polygon[j]["y"]

        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i

    return inside


def bbox_center_normalized(
    bbox: list[float], frame_width: int, frame_height: int
) -> tuple[float, float]:
    """Convert pixel bbox [x1,y1,x2,y2] to normalized center (0-1)."""
    cx = ((bbox[0] + bbox[2]) / 2) / frame_width
    cy = ((bbox[1] + bbox[3]) / 2) / frame_height
    return (cx, cy)


def bbox_bottom_center_normalized(
    bbox: list[float], frame_width: int, frame_height: int
) -> tuple[float, float]:
    """Convert pixel bbox to normalized bottom-center point (feet position)."""
    cx = ((bbox[0] + bbox[2]) / 2) / frame_width
    cy = bbox[3] / frame_height
    return (cx, cy)
