"""Training wrapper for YOLO-NAS via super-gradients.

super-gradients code is Apache-2.0, but the YOLO-NAS pretrained weights are under
LICENSE.YOLONAS.md, which forbids commercial use without an agreement with Deci.
"""

import time

from src.training.config import ExperimentRecord, TrainingConfig


def train_yolo_nas(config: TrainingConfig) -> ExperimentRecord:
    """Train YOLO-NAS-S using super-gradients Transfer Learning.

    Args:
        config: Training configuration

    Returns:
        ExperimentRecord with metrics and paths
    """
    record = ExperimentRecord(
        model_variant=config.model_variant,
        dataset=config.dataset_yaml,
        config={
            "epochs": config.epochs,
            "imgsz": config.imgsz,
            "batch_size": config.batch_size,
            "device": config.device,
            "seed": config.seed,
        },
        status="running",
    )

    try:
        from super_gradients.training import Trainer, models
        from super_gradients.training.dataloaders.dataloaders import (
            coco_detection_yolo_format_train,
            coco_detection_yolo_format_val,
        )
        from super_gradients.training.losses import PPYoloELoss
        from super_gradients.training.metrics import DetectionMetrics_050
        from super_gradients.training.models.detection_models.pp_yolo_e import (
            PPYoloEPostPredictionCallback,
        )
    except ImportError:
        record.status = "failed"
        record.metrics = {"error": "super-gradients not installed"}
        return record

    trainer = Trainer(experiment_name=config.name or "yolonas_person", ckpt_root_dir=config.project)

    model = models.get(
        "yolo_nas_s",
        pretrained_weights="coco" if config.pretrained else None,
        num_classes=1,
    )

    train_params = {
        "max_epochs": config.epochs,
        "initial_lr": config.lr0,
        "loss": PPYoloELoss(num_classes=1, reg_max=16),
        "valid_metrics_list": [
            DetectionMetrics_050(
                num_cls=1,
                score_thres=0.1,
                post_prediction_callback=PPYoloEPostPredictionCallback(
                    score_threshold=0.1, nms_top_k=1000, max_predictions=300, nms_threshold=0.7
                ),
            )
        ],
        "metric_to_watch": "mAP@0.50",
        "sg_logger": "dagshub_sg_logger" if False else None,
        "warmup_initial_lr": 1e-6,
        "warmup_mode": "LinearEpochLRWarmup",
        "cosine_final_lr_ratio": 0.01,
        "optimizer": "AdamW",
        "mixed_precision": config.device != "cpu",
    }

    start_time = time.time()

    try:
        trainer.train(
            model=model,
            training_params=train_params,
            train_loader=coco_detection_yolo_format_train(
                dataset_params={
                    "data_dir": str(config.dataset_yaml).replace("/dataset.yaml", ""),
                    "images_dir": "train/images",
                    "labels_dir": "train/labels",
                    "classes": ["person"],
                    "input_dim": [config.imgsz, config.imgsz],
                },
                dataloader_params={"batch_size": config.batch_size, "num_workers": config.workers},
            ),
            valid_loader=coco_detection_yolo_format_val(
                dataset_params={
                    "data_dir": str(config.dataset_yaml).replace("/dataset.yaml", ""),
                    "images_dir": "val/images",
                    "labels_dir": "val/labels",
                    "classes": ["person"],
                    "input_dim": [config.imgsz, config.imgsz],
                },
                dataloader_params={"batch_size": config.batch_size, "num_workers": config.workers},
            ),
        )
        record.status = "completed"
    except Exception as e:
        record.status = "failed"
        record.metrics = {"error": str(e)}

    record.duration_seconds = time.time() - start_time
    return record
