"""Tests for the rules evaluation engine."""

from datetime import datetime

import pytest

from src.rules.engine import RuleConfig, RulesEngine, schedule_is_active
from src.rules.zone import ZonePolygon


@pytest.fixture
def restricted_zone():
    return ZonePolygon(
        zone_id="z1",
        name="Bodega",
        zone_type="restricted",
        polygon_points=[
            {"x": 0.0, "y": 0.0},
            {"x": 0.5, "y": 0.0},
            {"x": 0.5, "y": 1.0},
            {"x": 0.0, "y": 1.0},
        ],
    )


@pytest.fixture
def monitored_zone():
    return ZonePolygon(
        zone_id="z2",
        name="Caja",
        zone_type="monitored",
        polygon_points=[
            {"x": 0.5, "y": 0.0},
            {"x": 1.0, "y": 0.0},
            {"x": 1.0, "y": 1.0},
            {"x": 0.5, "y": 1.0},
        ],
    )


def test_no_entry_triggers_on_person_in_restricted_zone(restricted_zone):
    engine = RulesEngine()
    engine.add_rule(RuleConfig(
        rule_id="r1",
        rule_type="no_entry",
        zone=restricted_zone,
        camera_id="cam1",
        parameters={},
        severity="high",
        cooldown_seconds=0,
    ))

    detections = [{"bbox": [50, 50, 150, 300], "confidence": 0.9, "track_id": 1}]
    events = engine.evaluate(detections, frame_width=640, frame_height=480)

    assert len(events) == 1
    assert events[0].event_type == "no_entry"
    assert events[0].zone_name == "Bodega"


def test_no_entry_does_not_trigger_outside_zone(restricted_zone):
    engine = RulesEngine()
    engine.add_rule(RuleConfig(
        rule_id="r1",
        rule_type="no_entry",
        zone=restricted_zone,
        camera_id="cam1",
        parameters={},
        cooldown_seconds=0,
    ))

    detections = [{"bbox": [400, 50, 500, 300], "confidence": 0.9, "track_id": 1}]
    events = engine.evaluate(detections, frame_width=640, frame_height=480)

    assert len(events) == 0


def test_cooldown_prevents_repeated_alerts(restricted_zone):
    engine = RulesEngine()
    engine.add_rule(RuleConfig(
        rule_id="r1",
        rule_type="no_entry",
        zone=restricted_zone,
        camera_id="cam1",
        parameters={},
        cooldown_seconds=300,
    ))

    detections = [{"bbox": [50, 50, 150, 300], "confidence": 0.9, "track_id": 1}]

    events1 = engine.evaluate(detections, 640, 480, current_time=1000.0)
    assert len(events1) == 1

    events2 = engine.evaluate(detections, 640, 480, current_time=1010.0)
    assert len(events2) == 0

    events3 = engine.evaluate(detections, 640, 480, current_time=1301.0)
    assert len(events3) == 1


def test_zone_abandoned_triggers_after_timeout(monitored_zone):
    engine = RulesEngine()
    engine.add_rule(RuleConfig(
        rule_id="r2",
        rule_type="zone_abandoned",
        zone=monitored_zone,
        camera_id="cam1",
        parameters={"timeout_seconds": 60},
        cooldown_seconds=0,
    ))

    occupied = [{"bbox": [400, 50, 500, 300], "confidence": 0.9, "track_id": 1}]
    engine.evaluate(occupied, 640, 480, current_time=1000.0)

    empty = []
    events = engine.evaluate(empty, 640, 480, current_time=1010.0)
    assert len(events) == 0

    events = engine.evaluate(empty, 640, 480, current_time=1070.0)
    assert len(events) == 1
    assert events[0].event_type == "zone_abandoned"


def test_empty_detections_no_events():
    engine = RulesEngine()
    events = engine.evaluate([], 640, 480)
    assert events == []


INSIDE_LEFT = [{"bbox": [50, 50, 150, 300], "confidence": 0.9, "track_id": 1}]
INSIDE_RIGHT = [{"bbox": [400, 50, 500, 300], "confidence": 0.9, "track_id": 1}]
MONDAY_NOON = datetime(2026, 11, 16, 12, 0)


def _state(engine, rule_id, now):
    return next(s for s in engine.get_states(now) if s["rule_id"] == rule_id)


def test_no_entry_waits_for_confirmation(restricted_zone):
    engine = RulesEngine()
    engine.add_rule(RuleConfig("r1", "no_entry", restricted_zone, "cam1", {"confirm_seconds": 2}, cooldown_seconds=0))

    assert engine.evaluate(INSIDE_LEFT, 640, 480, current_time=100.0) == []
    assert _state(engine, "r1", 100.0)["status"] == "confirming"
    assert _state(engine, "r1", 100.0)["seconds_to_alert"] == 2.0

    assert engine.evaluate(INSIDE_LEFT, 640, 480, current_time=101.0) == []
    events = engine.evaluate(INSIDE_LEFT, 640, 480, current_time=102.0)
    assert len(events) == 1 and events[0].rule_id == "r1"
    assert _state(engine, "r1", 102.0)["status"] == "intrusion"


def test_brief_false_detection_does_not_alert(restricted_zone):
    engine = RulesEngine()
    engine.add_rule(RuleConfig("r1", "no_entry", restricted_zone, "cam1", {"confirm_seconds": 2}, cooldown_seconds=0))
    engine.evaluate(INSIDE_LEFT, 640, 480, current_time=100.0)
    engine.evaluate([], 640, 480, current_time=101.0)
    assert engine.evaluate(INSIDE_LEFT, 640, 480, current_time=102.0) == []
    assert _state(engine, "r1", 102.0)["status"] == "confirming"


def test_abandoned_zone_counts_down_then_alerts(monitored_zone):
    engine = RulesEngine()
    engine.add_rule(RuleConfig("r2", "zone_abandoned", monitored_zone, "cam1", {"timeout_seconds": 60}, cooldown_seconds=300))

    engine.evaluate(INSIDE_RIGHT, 640, 480, current_time=1000.0)
    assert _state(engine, "r2", 1000.0)["status"] == "attended"

    engine.evaluate([], 640, 480, current_time=1010.0)
    engine.evaluate([], 640, 480, current_time=1040.0)
    state = _state(engine, "r2", 1040.0)
    assert state["status"] == "abandoned" and state["seconds_to_alert"] == 30.0

    assert len(engine.evaluate([], 640, 480, current_time=1070.0)) == 1
    state = _state(engine, "r2", 1100.0)
    assert state["status"] == "unattended" and state["next_alert_in"] == 270.0

    engine.evaluate(INSIDE_RIGHT, 640, 480, current_time=1110.0)
    assert _state(engine, "r2", 1110.0)["status"] == "attended"


def test_max_occupancy(restricted_zone):
    engine = RulesEngine()
    engine.add_rule(RuleConfig("r3", "max_occupancy", restricted_zone, "cam1", {"max_persons": 1}, cooldown_seconds=0))
    assert engine.evaluate(INSIDE_LEFT, 640, 480, current_time=1.0) == []
    two = INSIDE_LEFT + [{"bbox": [60, 60, 160, 310], "confidence": 0.8, "track_id": 2}]
    events = engine.evaluate(two, 640, 480, current_time=2.0)
    assert len(events) == 1 and events[0].persons_detected == 2


def test_rule_outside_schedule_is_inactive(restricted_zone):
    engine = RulesEngine()
    night = {"days": [0, 1, 2, 3, 4], "start": "22:00", "end": "06:00"}
    engine.add_rule(RuleConfig("r1", "no_entry", restricted_zone, "cam1", {}, cooldown_seconds=0, schedule=night))

    assert engine.evaluate(INSIDE_LEFT, 640, 480, current_time=1.0, local_time=MONDAY_NOON) == []
    assert _state(engine, "r1", 1.0)["status"] == "inactive"

    monday_23h = datetime(2026, 11, 16, 23, 0)
    assert len(engine.evaluate(INSIDE_LEFT, 640, 480, current_time=2.0, local_time=monday_23h)) == 1


@pytest.mark.parametrize("local, expected", [
    (datetime(2026, 11, 16, 23, 0), True),   # Monday night, window starts Monday
    (datetime(2026, 11, 17, 5, 59), True),   # Tuesday early morning, still Monday's window
    (datetime(2026, 11, 17, 6, 0), False),
    (datetime(2026, 11, 16, 5, 0), False),   # Monday early morning belongs to Sunday's window (not listed)
    (datetime(2026, 11, 22, 23, 0), False),  # Sunday night
])
def test_overnight_schedule(local, expected):
    assert schedule_is_active({"days": [0, 1, 2, 3, 4], "start": "22:00", "end": "06:00"}, local) is expected


def test_no_schedule_or_full_day_is_always_active():
    assert schedule_is_active(None, MONDAY_NOON)
    assert schedule_is_active({"days": [0], "start": "00:00", "end": "00:00"}, MONDAY_NOON)
    assert not schedule_is_active({"days": [6], "start": "00:00", "end": "00:00"}, MONDAY_NOON)


def test_set_rules_keeps_timers_of_unchanged_rules(monitored_zone, restricted_zone):
    engine = RulesEngine()
    abandoned = RuleConfig("r2", "zone_abandoned", monitored_zone, "cam1", {"timeout_seconds": 60}, cooldown_seconds=0)
    engine.set_rules([abandoned])
    engine.evaluate([], 640, 480, current_time=1000.0)

    engine.set_rules([abandoned, RuleConfig("r1", "no_entry", restricted_zone, "cam1", {}, cooldown_seconds=0)])
    engine.evaluate([], 640, 480, current_time=1030.0)
    assert _state(engine, "r2", 1030.0)["seconds_to_alert"] == 30.0
