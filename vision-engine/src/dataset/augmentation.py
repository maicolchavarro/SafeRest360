"""Data augmentation pipeline using albumentations."""

from pathlib import Path

import cv2
import numpy as np


def get_augmentation_pipeline():
    """Return an augmentation pipeline for indoor person detection."""
    try:
        import albumentations as A
    except ImportError:
        return None

    return A.Compose(
        [
            A.HorizontalFlip(p=0.5),
            A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.4),
            A.GaussNoise(std_range=(0.02, 0.05), p=0.3),
            A.MotionBlur(blur_limit=5, p=0.2),
            A.RandomScale(scale_limit=0.2, p=0.3),
            A.GaussianBlur(blur_limit=(3, 5), p=0.15),
        ],
        bbox_params=A.BboxParams(
            format="yolo",
            label_fields=["class_labels"],
            min_visibility=0.3,
        ),
    )


def augment_image(
    image: np.ndarray,
    bboxes: list[list[float]],
    class_labels: list[int],
    pipeline=None,
) -> tuple[np.ndarray, list[list[float]], list[int]]:
    """Apply augmentation to an image and its YOLO bboxes.

    Args:
        image: BGR numpy array
        bboxes: list of [x_center, y_center, w, h] (normalized)
        class_labels: list of class indices
        pipeline: albumentations pipeline (uses default if None)

    Returns:
        Augmented (image, bboxes, class_labels)
    """
    if pipeline is None:
        pipeline = get_augmentation_pipeline()
    if pipeline is None:
        return image, bboxes, class_labels

    result = pipeline(image=image, bboxes=bboxes, class_labels=class_labels)
    return result["image"], result["bboxes"], result["class_labels"]


def augment_dataset(
    source_dir: Path,
    output_dir: Path,
    augmentations_per_image: int = 2,
) -> int:
    """Generate augmented copies of a dataset.

    Returns:
        Number of augmented images created.
    """
    images_dir = source_dir / "images"
    labels_dir = source_dir / "labels"
    out_images = output_dir / "images"
    out_labels = output_dir / "labels"
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    pipeline = get_augmentation_pipeline()
    if pipeline is None:
        return 0

    count = 0
    for img_path in sorted(images_dir.glob("*")):
        if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        # output_dir may equal source_dir; never re-augment previous outputs
        if "_aug" in img_path.stem:
            continue

        label_path = labels_dir / (img_path.stem + ".txt")
        if not label_path.exists():
            continue

        image = cv2.imread(str(img_path))
        if image is None:
            continue

        lines = label_path.read_text().strip().split("\n")
        bboxes = []
        class_labels = []
        for line in lines:
            if not line.strip():
                continue
            parts = line.strip().split()
            x_c, y_c, w, h = [float(v) for v in parts[1:5]]
            x_min = max(0.0, x_c - w / 2)
            y_min = max(0.0, y_c - h / 2)
            x_max = min(1.0, x_c + w / 2)
            y_max = min(1.0, y_c + h / 2)
            w_new = x_max - x_min
            h_new = y_max - y_min
            if w_new <= 0.001 or h_new <= 0.001:
                continue
            bboxes.append([x_min + w_new / 2, y_min + h_new / 2, w_new, h_new])
            class_labels.append(int(float(parts[0])))

        for i in range(augmentations_per_image):
            aug_img, aug_bboxes, aug_labels = augment_image(
                image, bboxes, class_labels, pipeline
            )

            aug_name = f"{img_path.stem}_aug{i}{img_path.suffix}"
            cv2.imwrite(str(out_images / aug_name), aug_img)

            label_lines = []
            for cls, bbox in zip(aug_labels, aug_bboxes):
                label_lines.append(f"{int(cls)} {bbox[0]:.6f} {bbox[1]:.6f} {bbox[2]:.6f} {bbox[3]:.6f}")
            (out_labels / f"{img_path.stem}_aug{i}.txt").write_text("\n".join(label_lines))
            count += 1

    return count
