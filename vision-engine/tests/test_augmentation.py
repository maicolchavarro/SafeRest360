import cv2
import numpy as np

from src.dataset.augmentation import augment_dataset


def _write_sample(root, name, label_text, size=(240, 320)):
    (root / "images").mkdir(parents=True, exist_ok=True)
    (root / "labels").mkdir(parents=True, exist_ok=True)
    img = np.random.randint(0, 255, (*size, 3), dtype=np.uint8)
    cv2.imwrite(str(root / "images" / f"{name}.jpg"), img)
    (root / "labels" / f"{name}.txt").write_text(label_text)


def _read_labels(path):
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            parts = line.split()
            rows.append((parts[0], [float(v) for v in parts[1:]]))
    return rows


def test_creates_n_copies_per_image(tmp_path):
    src, out = tmp_path / "src", tmp_path / "out"
    for i in range(3):
        _write_sample(src, f"img{i}", "0 0.5 0.5 0.2 0.4")

    count = augment_dataset(src, out, augmentations_per_image=2)

    assert count == 6
    assert len(list((out / "images").glob("*.jpg"))) == 6
    assert len(list((out / "labels").glob("*.txt"))) == 6


def test_float_class_ids_are_written_as_ints(tmp_path):
    src, out = tmp_path / "src", tmp_path / "out"
    _write_sample(src, "img", "0.0 0.5 0.5 0.3 0.5\n")

    augment_dataset(src, out, augmentations_per_image=3)

    for label_file in (out / "labels").glob("*.txt"):
        for cls, _ in _read_labels(label_file):
            assert cls == "0"


def test_boxes_crossing_image_border_are_clipped(tmp_path):
    src, out = tmp_path / "src", tmp_path / "out"
    # COCO-derived boxes can extend slightly past the border after rounding
    _write_sample(src, "img", "0 0.98 0.5 0.1 0.4\n0 0.5 0.02 0.3 0.1\n")

    augment_dataset(src, out, augmentations_per_image=5)

    for label_file in (out / "labels").glob("*.txt"):
        for _, (xc, yc, w, h) in _read_labels(label_file):
            assert 0.0 <= xc - w / 2 + 1e-6 and xc + w / 2 - 1e-6 <= 1.0
            assert 0.0 <= yc - h / 2 + 1e-6 and yc + h / 2 - 1e-6 <= 1.0


def test_degenerate_boxes_are_dropped(tmp_path):
    src, out = tmp_path / "src", tmp_path / "out"
    _write_sample(src, "img", "0 1.0 0.5 0.0005 0.2\n0 0.5 0.5 0.2 0.2\n")

    augment_dataset(src, out, augmentations_per_image=1)

    rows = _read_labels(next((out / "labels").glob("*.txt")))
    assert len(rows) <= 1


def test_rerun_in_place_does_not_augment_previous_outputs(tmp_path):
    root = tmp_path / "train"
    _write_sample(root, "img", "0 0.5 0.5 0.2 0.2")

    assert augment_dataset(root, root, augmentations_per_image=2) == 2
    assert augment_dataset(root, root, augmentations_per_image=2) == 2
    assert len(list((root / "images").glob("*.jpg"))) == 3


def test_images_without_labels_are_skipped(tmp_path):
    src, out = tmp_path / "src", tmp_path / "out"
    _write_sample(src, "labeled", "0 0.5 0.5 0.2 0.2")
    cv2.imwrite(str(src / "images" / "orphan.jpg"), np.zeros((50, 50, 3), np.uint8))

    assert augment_dataset(src, out, augmentations_per_image=1) == 1
