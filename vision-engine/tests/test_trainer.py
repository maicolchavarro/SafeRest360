import json
from pathlib import Path

import pytest

from src.evaluation.compare import build_comparison_table
from src.training import trainer
from src.training.config import ExperimentRecord, VARIANT_CONFIGS

PRETRAINED = Path(__file__).resolve().parents[1] / "yolov8n.pt"


def test_overrides_do_not_leak_between_runs(tmp_path, monkeypatch):
    seen = []

    def fake_train(config):
        seen.append(config)
        return ExperimentRecord(model_variant=config.model_variant, status="completed")

    monkeypatch.setattr(trainer, "train_model", fake_train)

    trainer.run_experiment("yolov8n", "a.yaml", output_dir=str(tmp_path), epochs=1, device="cuda")
    trainer.run_experiment("yolov8n", "b.yaml", output_dir=str(tmp_path))

    assert seen[0].epochs == 1 and seen[0].device == "cuda"
    assert seen[1].epochs == 100 and seen[1].device == "cpu"
    assert seen[1].dataset_yaml == "b.yaml"
    assert VARIANT_CONFIGS["yolov8n"].dataset_yaml == ""


def test_record_json_has_fields_used_by_notebook(tmp_path, monkeypatch):
    monkeypatch.setattr(
        trainer,
        "train_model",
        lambda c: ExperimentRecord(model_variant=c.model_variant, weights_path="w.pt", status="completed"),
    )
    trainer.run_experiment("yolov8s", "d.yaml", output_dir=str(tmp_path))

    files = list(tmp_path.glob("exp_yolov8s_*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["model_variant"] == "yolov8s"
    assert data["weights_path"] == "w.pt"


def test_unknown_variant_is_rejected():
    with pytest.raises(ValueError):
        trainer.run_experiment("yolov99", "x.yaml")


@pytest.mark.skipif(not PRETRAINED.exists(), reason="yolov8n.pt not available")
def test_cpu_training_pipeline_end_to_end(tiny_dataset, tmp_path):
    """Pipeline check on synthetic data: 1 epoch on CPU. Not a quality metric."""
    _, dataset_yaml = tiny_dataset
    exp_dir = tmp_path / "experiments"

    record = trainer.run_experiment(
        "yolov8n",
        dataset_yaml,
        output_dir=str(exp_dir),
        pretrained_weights=str(PRETRAINED),
        project=str(tmp_path / "runs"),
        epochs=1,
        imgsz=320,
        batch_size=2,
        workers=0,
        device="cpu",
        mosaic=0.0,
        mixup=0.0,
        warmup_epochs=0,
    )

    assert record.status == "completed"
    assert record.epochs_completed == 1
    assert Path(record.weights_path).exists()
    assert {"precision", "recall", "mAP50", "mAP50_95"} <= record.metrics.keys()
    assert build_comparison_table(str(exp_dir))[0]["model"] == "yolov8n"
