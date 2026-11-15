"""Training wrapper for Ultralytics YOLOv8 variants."""

import time
from pathlib import Path

from src.training.config import ExperimentRecord, TrainingConfig


def train_yolov8(config: TrainingConfig) -> ExperimentRecord:
    """Train a YOLOv8 model using Transfer Learning.

    Loads pretrained COCO weights and fine-tunes on the person-only dataset.

    Args:
        config: Training configuration

    Returns:
        ExperimentRecord with metrics and paths
    """
    from ultralytics import YOLO

    record = ExperimentRecord(
        model_variant=config.model_variant,
        dataset=config.dataset_yaml,
        config={
            "epochs": config.epochs,
            "imgsz": config.imgsz,
            "batch_size": config.batch_size,
            "optimizer": config.optimizer,
            "lr0": config.lr0,
            "lrf": config.lrf,
            "device": config.device,
            "freeze": config.freeze,
            "seed": config.seed,
        },
        status="running",
    )

    model = YOLO(config.pretrained_weights)

    start_time = time.time()

    results = model.train(
        data=config.dataset_yaml,
        epochs=config.epochs,
        imgsz=config.imgsz,
        batch=config.batch_size,
        patience=config.patience,
        optimizer=config.optimizer,
        lr0=config.lr0,
        lrf=config.lrf,
        warmup_epochs=config.warmup_epochs,
        mosaic=config.mosaic,
        mixup=config.mixup,
        device=config.device,
        workers=config.workers,
        project=config.project,
        name=config.name,
        pretrained=config.pretrained,
        single_cls=config.single_cls,
        seed=config.seed,
        exist_ok=config.exist_ok,
        verbose=True,
    )

    elapsed = time.time() - start_time

    best_weights = Path(config.project) / config.name / "weights" / "best.pt"
    record.duration_seconds = elapsed
    record.weights_path = str(best_weights) if best_weights.exists() else ""
    record.status = "completed"

    if results and hasattr(results, "results_dict"):
        rd = results.results_dict
        record.metrics = {
            "precision": rd.get("metrics/precision(B)", 0),
            "recall": rd.get("metrics/recall(B)", 0),
            "mAP50": rd.get("metrics/mAP50(B)", 0),
            "mAP50_95": rd.get("metrics/mAP50-95(B)", 0),
        }
        # early stopping can end training before config.epochs
        record.epochs_completed = model.trainer.epoch + 1

    return record


def evaluate_yolov8(weights_path: str, dataset_yaml: str, device: str = "cpu") -> dict:
    """Evaluate a trained YOLOv8 model on the test set."""
    from ultralytics import YOLO

    model = YOLO(weights_path)
    results = model.val(data=dataset_yaml, device=device, split="test")

    return {
        "precision": float(results.results_dict.get("metrics/precision(B)", 0)),
        "recall": float(results.results_dict.get("metrics/recall(B)", 0)),
        "mAP50": float(results.results_dict.get("metrics/mAP50(B)", 0)),
        "mAP50_95": float(results.results_dict.get("metrics/mAP50-95(B)", 0)),
    }
