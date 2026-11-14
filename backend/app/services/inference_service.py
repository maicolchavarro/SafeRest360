"""Bridge between the FastAPI backend and the vision-engine package.

The vision-engine is imported in-process for the demo/dev setup.
In production this would be a gRPC or HTTP microservice.
"""

import sys
from pathlib import Path

VISION_ENGINE_ROOT = Path(__file__).resolve().parents[3] / "vision-engine"
if str(VISION_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(VISION_ENGINE_ROOT))

_detector = None
_tracker = None


def get_detector():
    global _detector
    if _detector is not None:
        return _detector
    try:
        from src.inference.detector import Detector
        _detector = Detector.get_instance()
    except Exception:
        _detector = None
    return _detector


def get_tracker():
    global _tracker
    if _tracker is not None:
        return _tracker
    try:
        from src.inference.tracker import PersonTracker
        _tracker = PersonTracker()
    except Exception:
        _tracker = None
    return _tracker


def detect_persons(frame, confidence: float = 0.5):
    detector = get_detector()
    if detector is None:
        return []
    return detector.detect(frame, confidence_threshold=confidence)


def detect_and_track(frame, confidence: float = 0.5):
    detector = get_detector()
    tracker = get_tracker()
    if detector is None:
        return []

    from src.inference.detector import Detection
    raw_dets = detector.detect_raw(frame, confidence_threshold=confidence)

    if tracker is not None:
        raw_dets = tracker.update(raw_dets)

    return [d.to_dict() for d in raw_dets]


def evaluate_rules(detections, zones_config, rules_config, frame_width, frame_height):
    """Run the rules engine against detections and zone/rule configs from DB."""
    try:
        from src.rules.engine import RulesEngine, RuleConfig
        from src.rules.zone import ZonePolygon
    except ImportError:
        return []

    engine = RulesEngine()
    for rule_cfg in rules_config:
        zone_data = zones_config.get(rule_cfg["zone_id"])
        if not zone_data:
            continue
        zone = ZonePolygon(
            zone_id=zone_data["id"],
            name=zone_data["name"],
            zone_type=zone_data["zone_type"],
            polygon_points=zone_data["polygon_points"],
        )
        engine.add_rule(RuleConfig(
            rule_id=rule_cfg["id"],
            rule_type=rule_cfg["rule_type"],
            zone=zone,
            camera_id=rule_cfg["camera_id"],
            parameters=rule_cfg.get("parameters", {}),
            severity=rule_cfg.get("severity", "medium"),
            cooldown_seconds=rule_cfg.get("cooldown_seconds", 300),
        ))

    return [e.__dict__ for e in engine.evaluate(detections, frame_width, frame_height)]
