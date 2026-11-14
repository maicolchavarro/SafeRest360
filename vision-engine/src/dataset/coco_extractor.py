"""Extract person-class images and annotations from COCO dataset into YOLO format."""

import json
import shutil
from collections import defaultdict
from pathlib import Path


COCO_PERSON_CATEGORY_ID = 1


def extract_person_subset(
    annotations_path: Path,
    images_dir: Path,
    output_dir: Path,
    max_images: int | None = None,
) -> dict:
    """Extract images containing persons from COCO and convert to YOLO format.

    Args:
        annotations_path: Path to COCO instances JSON (e.g. instances_train2017.json)
        images_dir: Path to COCO images directory
        output_dir: Where to write YOLO-formatted images/ and labels/
        max_images: Limit number of images (for testing)

    Returns:
        Stats dict with counts of images and annotations processed.
    """
    output_images = output_dir / "images"
    output_labels = output_dir / "labels"
    output_images.mkdir(parents=True, exist_ok=True)
    output_labels.mkdir(parents=True, exist_ok=True)

    with open(annotations_path) as f:
        coco = json.load(f)

    image_lookup = {img["id"]: img for img in coco["images"]}

    person_anns = defaultdict(list)
    for ann in coco["annotations"]:
        if ann["category_id"] == COCO_PERSON_CATEGORY_ID and ann.get("iscrowd", 0) == 0:
            person_anns[ann["image_id"]].append(ann)

    image_ids = list(person_anns.keys())
    if max_images:
        image_ids = image_ids[:max_images]

    copied = 0
    total_anns = 0

    for image_id in image_ids:
        img_info = image_lookup.get(image_id)
        if img_info is None:
            continue

        filename = img_info["file_name"]
        src_path = images_dir / filename
        if not src_path.exists():
            continue

        shutil.copy2(src_path, output_images / filename)

        w, h = img_info["width"], img_info["height"]
        label_lines = []
        for ann in person_anns[image_id]:
            bbox = ann["bbox"]  # [x, y, width, height] in pixels
            x_center = (bbox[0] + bbox[2] / 2) / w
            y_center = (bbox[1] + bbox[3] / 2) / h
            bw = bbox[2] / w
            bh = bbox[3] / h

            x_center = max(0, min(1, x_center))
            y_center = max(0, min(1, y_center))
            bw = max(0, min(1, bw))
            bh = max(0, min(1, bh))

            if bw > 0.001 and bh > 0.001:
                label_lines.append(f"0 {x_center:.6f} {y_center:.6f} {bw:.6f} {bh:.6f}")
                total_anns += 1

        label_file = output_labels / (Path(filename).stem + ".txt")
        label_file.write_text("\n".join(label_lines))
        copied += 1

    return {
        "images_processed": copied,
        "annotations_total": total_anns,
        "output_dir": str(output_dir),
    }


def create_dataset_yaml(dataset_dir: Path, output_path: Path | None = None) -> Path:
    """Generate a YOLO dataset.yaml file."""
    yaml_path = output_path or dataset_dir / "dataset.yaml"
    content = f"""path: {dataset_dir.resolve()}
train: train/images
val: val/images
test: test/images

nc: 1
names: ['person']
"""
    yaml_path.write_text(content)
    return yaml_path
