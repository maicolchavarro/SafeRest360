import numpy as np
import pytest

from src.evaluation.person_eval import coco_map, load_split, precision_recall_at


def _sample(boxes):
    return {"path": None, "width": 640, "height": 480, "boxes": np.array(boxes, dtype=float).reshape(-1, 4)}


def _pred(rows):
    return np.array(rows, dtype=float).reshape(-1, 5)


def test_perfect_predictions_score_one():
    samples = [_sample([[10, 10, 110, 210], [300, 50, 400, 300]])]
    preds = [_pred([[10, 10, 110, 210, 0.9], [300, 50, 400, 300, 0.8]])]
    pr = precision_recall_at(samples, preds, 0.5)
    assert pr["precision"] == 1.0 and pr["recall"] == 1.0
    pytest.importorskip("pycocotools")
    m = coco_map(samples, preds)
    assert m["mAP50"] == pytest.approx(1.0) and m["mAP50_95"] == pytest.approx(1.0)


def test_false_positive_and_missed_person():
    samples = [_sample([[10, 10, 110, 210], [300, 50, 400, 300]])]
    preds = [_pred([[10, 10, 110, 210, 0.9], [500, 300, 600, 400, 0.7]])]
    pr = precision_recall_at(samples, preds, 0.5)
    assert (pr["tp"], pr["fp"], pr["fn"]) == (1, 1, 1)
    assert pr["precision"] == 0.5 and pr["recall"] == 0.5


def test_low_confidence_detections_ignored_at_operating_threshold():
    samples = [_sample([[10, 10, 110, 210]])]
    preds = [_pred([[10, 10, 110, 210, 0.3]])]
    assert precision_recall_at(samples, preds, 0.5)["recall"] == 0.0
    assert precision_recall_at(samples, preds, 0.25)["recall"] == 1.0


def test_one_detection_cannot_match_two_people():
    samples = [_sample([[10, 10, 110, 210], [12, 12, 112, 212]])]
    preds = [_pred([[10, 10, 110, 210, 0.9]])]
    pr = precision_recall_at(samples, preds, 0.5)
    assert (pr["tp"], pr["fn"]) == (1, 1)


def test_load_split_converts_yolo_labels_to_pixels(tiny_dataset):
    root, _ = tiny_dataset
    samples = load_split(root / "val")
    assert len(samples) == 3
    s = samples[0]
    assert s["width"] == 320 and s["boxes"].shape == (1, 4)
    x1, y1, x2, y2 = s["boxes"][0]
    assert 0 <= x1 < x2 <= 320 and 0 <= y1 < y2 <= 320
