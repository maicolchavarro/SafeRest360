"""Tests for the rules evaluation engine."""

import pytest

from src.rules.engine import RuleConfig, RulesEngine
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
