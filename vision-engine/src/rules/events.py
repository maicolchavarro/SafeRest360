"""Event data structures for the rules engine."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Event:
    event_type: str  # "no_entry", "zone_abandoned", "max_occupancy"
    zone_id: str
    zone_name: str
    camera_id: str
    severity: str
    description: str
    persons_detected: int
    detection_data: list[dict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "camera_id": self.camera_id,
            "severity": self.severity,
            "description": self.description,
            "persons_detected": self.persons_detected,
            "detection_data": self.detection_data,
            "timestamp": self.timestamp.isoformat(),
        }
