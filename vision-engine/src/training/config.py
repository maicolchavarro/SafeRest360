"""Training configuration dataclasses."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TrainingConfig:
    model_variant: str = "yolov8n"
    pretrained_weights: str = "yolov8n.pt"
    dataset_yaml: str = ""
    epochs: int = 100
    imgsz: int = 640
    batch_size: int = 16
    patience: int = 20
    optimizer: str = "AdamW"
    lr0: float = 0.001
    lrf: float = 0.01
    warmup_epochs: int = 3
    mosaic: float = 1.0
    mixup: float = 0.1
    device: str = "cpu"
    workers: int = 4
    project: str = "runs/train"
    name: str = ""
    pretrained: bool = True
    freeze: int = 0
    single_cls: bool = True
    seed: int = 42
    exist_ok: bool = True

    def __post_init__(self):
        if not self.name:
            self.name = f"{self.model_variant}_person"


@dataclass
class ExperimentRecord:
    experiment_id: str = ""
    model_variant: str = ""
    version: str = "1.0"
    dataset: str = ""
    config: dict = field(default_factory=dict)
    hardware: str = ""
    duration_seconds: float = 0.0
    epochs_completed: int = 0
    metrics: dict = field(default_factory=dict)
    weights_path: str = ""
    status: str = "pending"
    mlflow_run_id: str = ""


VARIANT_CONFIGS = {
    "yolov8n": TrainingConfig(
        model_variant="yolov8n",
        pretrained_weights="yolov8n.pt",
        batch_size=16,
    ),
    "yolov8s": TrainingConfig(
        model_variant="yolov8s",
        pretrained_weights="yolov8s.pt",
        batch_size=16,
    ),
    "yolov8m": TrainingConfig(
        model_variant="yolov8m",
        pretrained_weights="yolov8m.pt",
        batch_size=8,
    ),
    "yolonas_s": TrainingConfig(
        model_variant="yolonas_s",
        pretrained_weights="coco",
        batch_size=16,
    ),
}


def get_cpu_test_config(variant: str = "yolov8n") -> TrainingConfig:
    """Return a minimal config for CPU functional testing."""
    cfg = TrainingConfig(
        model_variant=variant,
        pretrained_weights=f"{variant}.pt" if "yolonas" not in variant else "coco",
        epochs=2,
        imgsz=320,
        batch_size=2,
        workers=0,
        device="cpu",
        patience=5,
        warmup_epochs=1,
        mosaic=0.0,
        mixup=0.0,
    )
    return cfg
