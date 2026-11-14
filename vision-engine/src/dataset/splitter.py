"""Split a YOLO-format dataset into train/val/test sets."""

import random
import shutil
from pathlib import Path


def split_dataset(
    source_dir: Path,
    output_dir: Path,
    train_ratio: float = 0.7,
    val_ratio: float = 0.2,
    test_ratio: float = 0.1,
    seed: int = 42,
) -> dict:
    """Split images and labels into train/val/test directories.

    Args:
        source_dir: Directory with images/ and labels/ subdirectories
        output_dir: Where to create train/, val/, test/ each with images/ and labels/
        train_ratio, val_ratio, test_ratio: Split proportions (must sum to 1.0)
        seed: Random seed for reproducibility

    Returns:
        Stats dict with counts per split.
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6

    images_dir = source_dir / "images"
    labels_dir = source_dir / "labels"

    image_files = sorted(
        [f for f in images_dir.iterdir() if f.suffix.lower() in (".jpg", ".jpeg", ".png")]
    )

    random.seed(seed)
    random.shuffle(image_files)

    n = len(image_files)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    splits = {
        "train": image_files[:n_train],
        "val": image_files[n_train : n_train + n_val],
        "test": image_files[n_train + n_val :],
    }

    stats = {}
    for split_name, files in splits.items():
        split_images = output_dir / split_name / "images"
        split_labels = output_dir / split_name / "labels"
        split_images.mkdir(parents=True, exist_ok=True)
        split_labels.mkdir(parents=True, exist_ok=True)

        for img_file in files:
            shutil.copy2(img_file, split_images / img_file.name)
            label_file = labels_dir / (img_file.stem + ".txt")
            if label_file.exists():
                shutil.copy2(label_file, split_labels / label_file.name)

        stats[split_name] = len(files)

    return stats
