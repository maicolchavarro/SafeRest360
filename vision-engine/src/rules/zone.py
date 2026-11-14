"""Zone polygon class for detection zone management."""

from src.utils.geometry import point_in_polygon


class ZonePolygon:
    """Represents a monitored zone defined by a polygon."""

    def __init__(
        self,
        zone_id: str,
        name: str,
        zone_type: str,
        polygon_points: list[dict],
        color: str = "#FF0000",
    ):
        self.zone_id = zone_id
        self.name = name
        self.zone_type = zone_type
        self.polygon_points = polygon_points
        self.color = color

    def contains_point(self, point: tuple[float, float]) -> bool:
        """Check if a normalized point (0-1) is inside this zone."""
        return point_in_polygon(point, self.polygon_points)

    def count_persons_inside(
        self,
        detections: list[dict],
        frame_width: int,
        frame_height: int,
        use_bottom_center: bool = True,
    ) -> list[dict]:
        """Return detections whose reference point falls inside this zone.

        Args:
            detections: List of detection dicts with "bbox" key
            frame_width, frame_height: Frame dimensions for normalization
            use_bottom_center: Use bottom-center (feet) instead of center

        Returns:
            List of detections inside the zone
        """
        from src.utils.geometry import bbox_bottom_center_normalized, bbox_center_normalized

        inside = []
        for det in detections:
            bbox = det["bbox"]
            if use_bottom_center:
                point = bbox_bottom_center_normalized(bbox, frame_width, frame_height)
            else:
                point = bbox_center_normalized(bbox, frame_width, frame_height)

            if self.contains_point(point):
                inside.append(det)

        return inside
