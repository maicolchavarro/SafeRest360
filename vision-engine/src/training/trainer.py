"""Unified training interface dispatching to framework-specific trainers."""

import dataclasses
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.training.config import ExperimentRecord, TrainingConfig, VARIANT_CONFIGS


def train_model(config: TrainingConfig) -> ExperimentRecord:
    """Train a model using the appropriate framework.

    Dispatches to Ultralytics (YOLOv8) or super-gradients (YOLO-NAS)
    based on the variant name.
    """
    if "yolonas" in config.model_variant:
        from src.training.train_yolonas import train_yolo_nas
        return train_yolo_nas(config)
    else:
        from src.training.train_ultralytics import train_yolov8
        return train_yolov8(config)


def run_experiment(
    variant: str,
    dataset_yaml: str,
    output_dir: str = "experiments",
    **overrides,
) -> ExperimentRecord:
    """Run a complete training experiment with logging.

    Args:
        variant: Model variant key (yolov8n, yolov8s, yolov8m, yolonas_s)
        dataset_yaml: Path to dataset.yaml
        output_dir: Where to save experiment records
        **overrides: Override any TrainingConfig field

    Returns:
        ExperimentRecord with full experiment details
    """
    if variant not in VARIANT_CONFIGS:
        raise ValueError(f"Unknown variant: {variant}. Available: {list(VARIANT_CONFIGS.keys())}")

    config = dataclasses.replace(VARIANT_CONFIGS[variant], dataset_yaml=dataset_yaml)

    for key, value in overrides.items():
        if hasattr(config, key):
            setattr(config, key, value)

    experiment_id = f"exp_{variant}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    import platform
    record = train_model(config)
    record.experiment_id = experiment_id
    record.hardware = f"{platform.processor()} | device={config.device}"

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    record_file = output_path / f"{experiment_id}.json"

    record_dict = {
        "experiment_id": record.experiment_id,
        "model_variant": record.model_variant,
        "version": record.version,
        "dataset": record.dataset,
        "config": record.config,
        "hardware": record.hardware,
        "duration_seconds": record.duration_seconds,
        "epochs_completed": record.epochs_completed,
        "metrics": record.metrics,
        "weights_path": record.weights_path,
        "status": record.status,
        "mlflow_run_id": record.mlflow_run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    record_file.write_text(json.dumps(record_dict, indent=2))

    return record


def compare_experiments(experiment_dir: str = "experiments") -> list[dict]:
    """Load all experiment records and return a comparison table."""
    experiments = []
    for f in sorted(Path(experiment_dir).glob("exp_*.json")):
        data = json.loads(f.read_text())
        experiments.append(data)
    return experiments
