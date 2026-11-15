"""Rules evaluation engine for generating events from detections."""

import time
from collections import defaultdict

from src.rules.events import Event
from src.rules.zone import ZonePolygon


class RuleConfig:
    """Configuration for a single rule."""

    def __init__(
        self,
        rule_id: str,
        rule_type: str,
        zone: ZonePolygon,
        camera_id: str,
        parameters: dict,
        severity: str = "medium",
        cooldown_seconds: int = 300,
        schedule: dict | None = None,
    ):
        self.rule_id = rule_id
        self.rule_type = rule_type
        self.zone = zone
        self.camera_id = camera_id
        self.parameters = parameters
        self.severity = severity
        self.cooldown_seconds = cooldown_seconds
        self.schedule = schedule


class RulesEngine:
    """Evaluate rules against detections and generate events.

    Handles:
    - no_entry: Person detected in restricted zone
    - zone_abandoned: No person in required-presence zone for timeout
    - max_occupancy: Too many persons in a zone

    Includes cooldown to prevent alert flooding.
    """

    def __init__(self):
        self._rules: list[RuleConfig] = []
        self._last_alert_time: dict[str, float] = {}
        self._zone_empty_since: dict[str, float] = defaultdict(lambda: 0.0)
        self._zone_occupied: dict[str, bool] = defaultdict(lambda: False)

    def add_rule(self, rule: RuleConfig):
        self._rules.append(rule)

    def clear_rules(self):
        self._rules.clear()
        self._last_alert_time.clear()
        self._zone_empty_since.clear()

    def evaluate(
        self,
        detections: list[dict],
        frame_width: int,
        frame_height: int,
        current_time: float | None = None,
    ) -> list[Event]:
        """Evaluate all rules against current detections.

        Args:
            detections: Person detections with "bbox" key
            frame_width, frame_height: Frame dimensions
            current_time: Timestamp (uses time.time() if None)

        Returns:
            List of triggered events
        """
        now = current_time or time.time()
        events = []

        for rule in self._rules:
            first_new = len(events)
            persons_inside = rule.zone.count_persons_inside(
                detections, frame_width, frame_height
            )
            count = len(persons_inside)

            if rule.rule_type == "no_entry":
                if count > 0 and self._check_cooldown(rule.rule_id, now, rule.cooldown_seconds):
                    events.append(Event(
                        event_type="no_entry",
                        zone_id=rule.zone.zone_id,
                        zone_name=rule.zone.name,
                        camera_id=rule.camera_id,
                        severity=rule.severity,
                        description=f"Persona detectada en zona restringida: {rule.zone.name}",
                        persons_detected=count,
                        detection_data=[d for d in persons_inside],
                    ))
                    self._last_alert_time[rule.rule_id] = now

            elif rule.rule_type == "zone_abandoned":
                timeout = rule.parameters.get("timeout_seconds", 300)
                zone_key = f"abandoned_{rule.rule_id}"

                if count == 0:
                    if self._zone_occupied.get(zone_key, True):
                        self._zone_empty_since[zone_key] = now
                        self._zone_occupied[zone_key] = False

                    empty_duration = now - self._zone_empty_since.get(zone_key, now)
                    if empty_duration >= timeout and self._check_cooldown(rule.rule_id, now, rule.cooldown_seconds):
                        events.append(Event(
                            event_type="zone_abandoned",
                            zone_id=rule.zone.zone_id,
                            zone_name=rule.zone.name,
                            camera_id=rule.camera_id,
                            severity=rule.severity,
                            description=f"Zona sin personal por {int(empty_duration)}s: {rule.zone.name}",
                            persons_detected=0,
                        ))
                        self._last_alert_time[rule.rule_id] = now
                else:
                    self._zone_occupied[zone_key] = True

            elif rule.rule_type == "max_occupancy":
                max_persons = rule.parameters.get("max_persons", 5)
                if count > max_persons and self._check_cooldown(rule.rule_id, now, rule.cooldown_seconds):
                    events.append(Event(
                        event_type="max_occupancy",
                        zone_id=rule.zone.zone_id,
                        zone_name=rule.zone.name,
                        camera_id=rule.camera_id,
                        severity=rule.severity,
                        description=f"Ocupación excesiva ({count}/{max_persons}) en: {rule.zone.name}",
                        persons_detected=count,
                        detection_data=[d for d in persons_inside],
                    ))
                    self._last_alert_time[rule.rule_id] = now

            for event in events[first_new:]:
                event.rule_id = rule.rule_id

        return events

    def _check_cooldown(self, rule_id: str, now: float, cooldown: int) -> bool:
        last = self._last_alert_time.get(rule_id)
        if last is None:
            return True
        return (now - last) >= cooldown
