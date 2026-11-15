from src.inference.detector import Detection
from src.inference.tracker import PersonTracker


def _frame(offset):
    return [
        Detection([100 + offset, 50, 200 + offset, 300], 0.9),
        Detection([400 - offset, 100, 500 - offset, 350], 0.9),
    ]


def test_ids_are_stable_while_people_move():
    tracker = PersonTracker()
    history = [tracker.update(_frame(i * 3)) for i in range(8)]

    first_ids = sorted(d.track_id for d in history[0])
    assert len(set(first_ids)) == 2 and all(i >= 0 for i in first_ids)
    for frame in history[1:]:
        assert sorted(d.track_id for d in frame) == first_ids


def test_each_person_keeps_their_own_id():
    tracker = PersonTracker()
    left_ids = set()
    for i in range(8):
        tracked = tracker.update(_frame(i * 3))
        left = min(tracked, key=lambda d: d.bbox[0])
        left_ids.add(left.track_id)
    assert len(left_ids) == 1


def test_empty_frame_returns_empty():
    assert PersonTracker().update([]) == []


def test_reset_clears_state():
    tracker = PersonTracker()
    for i in range(3):
        tracker.update(_frame(i))
    tracker.reset()
    assert len(tracker.update(_frame(0))) == 2
