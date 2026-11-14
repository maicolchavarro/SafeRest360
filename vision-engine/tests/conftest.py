"""Test fixtures for vision engine tests."""

import json
import shutil
from pathlib import Path

import cv2
import numpy as np
import pytest


@pytest.fixture
def tiny_dataset(tmp_path):
    """Create a minimal YOLO-format dataset for testing.

    Generates synthetic images with colored rectangles simulating persons
    and corresponding YOLO labels.
    """
    for split in ["train", "val", "test"]:
        images_dir = tmp_path / split / "images"
        labels_dir = tmp_path / split / "labels"
        images_dir.mkdir(parents=True)
        labels_dir.mkdir(parents=True)

        n_images = 6 if split == "train" else 3
        for i in range(n_images):
            img = np.random.randint(100, 200, (320, 320, 3), dtype=np.uint8)

            x1 = np.random.randint(50, 150)
            y1 = np.random.randint(30, 100)
            x2 = x1 + np.random.randint(40, 80)
            y2 = y1 + np.random.randint(80, 160)
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), -1)

            cv2.imwrite(str(images_dir / f"img_{split}_{i:03d}.jpg"), img)

            cx = ((x1 + x2) / 2) / 320
            cy = ((y1 + y2) / 2) / 320
            bw = (x2 - x1) / 320
            bh = (y2 - y1) / 320
            label = f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}"
            (labels_dir / f"img_{split}_{i:03d}.txt").write_text(label)

    dataset_yaml = tmp_path / "dataset.yaml"
    dataset_yaml.write_text(
        f"path: {tmp_path}\n"
        f"train: train/images\n"
        f"val: val/images\n"
        f"test: test/images\n"
        f"nc: 1\n"
        f"names: ['person']\n"
    )

    return tmp_path, str(dataset_yaml)


@pytest.fixture
def sample_frame():
    """Create a sample BGR frame with synthetic person-like rectangles."""
    frame = np.random.randint(100, 200, (480, 640, 3), dtype=np.uint8)
    cv2.rectangle(frame, (100, 50), (200, 300), (0, 0, 255), -1)
    cv2.rectangle(frame, (400, 100), (500, 350), (255, 0, 0), -1)
    return frame


@pytest.fixture
def sample_zone():
    """A sample restricted zone polygon (normalized coordinates)."""
    return {
        "zone_id": "zone-test-1",
        "name": "Bodega",
        "zone_type": "restricted",
        "polygon_points": [
            {"x": 0.0, "y": 0.0},
            {"x": 0.5, "y": 0.0},
            {"x": 0.5, "y": 0.5},
            {"x": 0.0, "y": 0.5},
        ],
    }
