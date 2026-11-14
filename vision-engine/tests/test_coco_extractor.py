"""Tests for COCO person class extractor."""

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from src.dataset.coco_extractor import create_dataset_yaml, extract_person_subset


@pytest.fixture
def mock_coco(tmp_path):
    """Create a minimal mock COCO annotation structure."""
    images_dir = tmp_path / "images"
    images_dir.mkdir()

    images = []
    annotations = []
    for i in range(5):
        img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        filename = f"img_{i:04d}.jpg"
        cv2.imwrite(str(images_dir / filename), img)
        images.append({"id": i, "file_name": filename, "width": 100, "height": 100})

        annotations.append({
            "id": i * 10,
            "image_id": i,
            "category_id": 1,
            "bbox": [10, 10, 30, 60],
            "area": 1800,
            "iscrowd": 0,
        })

    annotations.append({
        "id": 999,
        "image_id": 0,
        "category_id": 18,
        "bbox": [50, 50, 20, 20],
        "area": 400,
        "iscrowd": 0,
    })

    coco_json = {
        "images": images,
        "annotations": annotations,
        "categories": [{"id": 1, "name": "person"}, {"id": 18, "name": "dog"}],
    }

    ann_path = tmp_path / "annotations.json"
    ann_path.write_text(json.dumps(coco_json))

    return ann_path, images_dir


def test_extract_person_subset(mock_coco, tmp_path):
    ann_path, images_dir = mock_coco
    output_dir = tmp_path / "output"

    stats = extract_person_subset(ann_path, images_dir, output_dir)

    assert stats["images_processed"] == 5
    assert stats["annotations_total"] == 5

    label_files = list((output_dir / "labels").glob("*.txt"))
    assert len(label_files) == 5

    label_content = label_files[0].read_text().strip()
    parts = label_content.split()
    assert parts[0] == "0"
    assert len(parts) == 5
    for val in parts[1:]:
        assert 0 <= float(val) <= 1


def test_extract_with_max_images(mock_coco, tmp_path):
    ann_path, images_dir = mock_coco
    output_dir = tmp_path / "output_limited"

    stats = extract_person_subset(ann_path, images_dir, output_dir, max_images=2)
    assert stats["images_processed"] == 2


def test_create_dataset_yaml(tmp_path):
    yaml_path = create_dataset_yaml(tmp_path)
    assert yaml_path.exists()
    content = yaml_path.read_text()
    assert "nc: 1" in content
    assert "person" in content
