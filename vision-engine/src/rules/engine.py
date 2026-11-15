"""Rules evaluation engine: turns per-frame detections into events and a live state per rule."""

import time
from dataclasses import dataclass
from datetime import datetime
from datetime import time as dtime

from src.rules.events import Event
from src.rules.zone import ZonePolygon

# Statuses exposed to the UI
INACTIVE = "inactive"            # outside the rule's schedule
CLEAR = "clear"                  # no_entry / max_occupancy: nothing to report
CONFIRMING = "confirming"        # condition seen, waiting confirm_seconds before alerting
INTRUSION = "intrusion"          # no_entry confirmed
OVER_CAPACITY = "over_capacity"  # max_occupancy confirmed
ATTENDED = "attended"            # zone_abandoned: someone is in the zone
ABANDONED = "abandoned"          # zone_abandoned: empty, counting down to the alert
UNATTENDED = "unattended"        # zone_abandoned: empty past the timeout


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
        self.parameters = parameters or {}
        self.severity = severity
        self.cooldown_seconds = cooldown_seconds
        self.schedule = schedule


def _parse_hhmm(value: str) -> dtime:
    hours, minutes = value.split(":")
    return dtime(int(hours), int(minutes))


def schedule_is_active(schedule: dict | None, local: datetime) -> bool:
    """schedule = {"days": [0..6] (0 = Monday), "start": "HH:MM", "end": "HH:MM"}.

    An end at or before the start is an overnight window (22:00-06:00 belongs to the day it starts).
    start == end means the whole day.
    """
    if not schedule:
        return True
    days = schedule.get("days")
    days = set(range(7)) if days is None else set(days)
    start = _parse_hhmm(schedule.get("start", "00:00"))
    end = _parse_hhmm(schedule.get("end", "00:00"))
    now, weekday = local.time(), local.weekday()

    if start == end:
        return weekday in days
    if start < end:
        return start <= now < end and weekday in days
    if now >= start:
        return weekday in days
    if now < end:
        return (weekday - 1) % 7 in days
    return False


@dataclass
class _RuleRuntime:
    since: float | None = None        # when the current condition started (occupied / empty / over capacity)
    last_alert: float | None = None
    status: str = CLEAR
    persons: int = 0
    seconds_to_alert: float | None = None


class RulesEngine:
    """Evaluate rules against detections and generate events.

    - no_entry: person in a restricted zone for confirm_seconds (default 0)
    - zone_abandoned: nobody in the zone for timeout_seconds (default 300)
    - max_occupancy: more than max_persons for confirm_seconds (default 0)

    Each rule has a cooldown between alerts and an optional weekly schedule.
    """

    def __init__(self):
        self._rules: list[RuleConfig] = []
        self._runtime: dict[str, _RuleRuntime] = {}

    def add_rule(self, rule: RuleConfig):
        self._rules.append(rule)
        self._runtime.setdefault(rule.rule_id, _RuleRuntime())

    def set_rules(self, rules: list[RuleConfig]):
        """Replace the rule set, keeping timers and cooldowns of rules that are still present."""
        keep = {r.rule_id for r in rules}
        self._runtime = {rid: rt for rid, rt in self._runtime.items() if rid in keep}
        self._rules = []
        for rule in rules:
            self.add_rule(rule)

    def clear_rules(self):
        self._rules.clear()
        self._runtime.clear()

    def evaluate(
        self,
        detections: list[dict],
        frame_width: int,
        frame_height: int,
        current_time: float | None = None,
        local_time: datetime | None = None,
    ) -> list[Event]:
        """Evaluate all rules against the current detections.

        current_time drives timers (monotonic seconds); local_time (restaurant timezone) drives schedules.
        """
        now = current_time if current_time is not None else time.time()
        local = local_time or datetime.now()
        events: list[Event] = []

        for rule in self._rules:
            rt = self._runtime[rule.rule_id]
            rt.seconds_to_alert = None

            if not schedule_is_active(rule.schedule, local):
                rt.since, rt.status, rt.persons = None, INACTIVE, 0
                continue

            inside = rule.zone.count_persons_inside(detections, frame_width, frame_height)
            rt.persons = len(inside)

            if rule.rule_type == "no_entry":
                event = self._check_presence(rule, rt, now, triggered=rt.persons > 0, alert_status=INTRUSION,
                                             description=f"Persona detectada en zona restringida: {rule.zone.name}",
                                             inside=inside)
            elif rule.rule_type == "max_occupancy":
                max_persons = rule.parameters.get("max_persons", 5)
                event = self._check_presence(rule, rt, now, triggered=rt.persons > max_persons,
                                             alert_status=OVER_CAPACITY,
                                             description=f"Ocupación excesiva ({rt.persons}/{max_persons}) en: {rule.zone.name}",
                                             inside=inside)
            elif rule.rule_type == "zone_abandoned":
                event = self._check_abandoned(rule, rt, now)
            else:
                continue

            if event is not None:
                event.rule_id = rule.rule_id
                events.append(event)

        return events

    def _cooldown_over(self, rule: RuleConfig, rt: _RuleRuntime, now: float) -> bool:
        return rt.last_alert is None or (now - rt.last_alert) >= rule.cooldown_seconds

    def _event(self, rule: RuleConfig, event_type: str, description: str, persons: int, inside: list[dict]) -> Event:
        return Event(
            event_type=event_type,
            zone_id=rule.zone.zone_id,
            zone_name=rule.zone.name,
            camera_id=rule.camera_id,
            severity=rule.severity,
            description=description,
            persons_detected=persons,
            detection_data=list(inside),
        )

    def _check_presence(self, rule, rt, now, triggered, alert_status, description, inside) -> Event | None:
        if not triggered:
            rt.since, rt.status = None, CLEAR
            return None
        if rt.since is None:
            rt.since = now
        remaining = rule.parameters.get("confirm_seconds", 0) - (now - rt.since)
        if remaining > 0:
            rt.status, rt.seconds_to_alert = CONFIRMING, remaining
            return None
        rt.status = alert_status
        if self._cooldown_over(rule, rt, now):
            rt.last_alert = now
            return self._event(rule, rule.rule_type, description, rt.persons, inside)
        return None

    def _check_abandoned(self, rule, rt, now) -> Event | None:
        if rt.persons > 0:
            rt.since, rt.status = None, ATTENDED
            return None
        if rt.since is None:
            rt.since = now
        empty_for = now - rt.since
        remaining = rule.parameters.get("timeout_seconds", 300) - empty_for
        if remaining > 0:
            rt.status, rt.seconds_to_alert = ABANDONED, remaining
            return None
        rt.status = UNATTENDED
        if self._cooldown_over(rule, rt, now):
            rt.last_alert = now
            return self._event(rule, "zone_abandoned", f"Zona sin personal por {int(empty_for)}s: {rule.zone.name}", 0, [])
        return None

    def get_states(self, current_time: float | None = None) -> list[dict]:
        """Live state of every rule, as of the last evaluate() call."""
        now = current_time if current_time is not None else time.time()
        states = []
        for rule in self._rules:
            rt = self._runtime[rule.rule_id]
            next_alert_in = None
            if rt.status in (INTRUSION, OVER_CAPACITY, UNATTENDED) and rt.last_alert is not None:
                next_alert_in = max(0.0, rule.cooldown_seconds - (now - rt.last_alert))
            states.append({
                "rule_id": rule.rule_id,
                "zone_id": rule.zone.zone_id,
                "rule_type": rule.rule_type,
                "status": rt.status,
                "persons": rt.persons,
                "seconds_to_alert": None if rt.seconds_to_alert is None else round(rt.seconds_to_alert, 1),
                "next_alert_in": None if next_alert_in is None else round(next_alert_in, 1),
                "condition_seconds": None if rt.since is None else round(now - rt.since, 1),
            })
        return states
