import json

from src.evaluation.compare import build_comparison_table, format_comparison_markdown


def _write_exp(d, name, variant, metrics, status="completed"):
    (d / f"exp_{name}.json").write_text(
        json.dumps(
            {
                "model_variant": variant,
                "metrics": metrics,
                "duration_seconds": 120.4,
                "epochs_completed": 42,
                "status": status,
            }
        )
    )


def test_table_reads_all_experiments(tmp_path):
    _write_exp(tmp_path, "a", "yolov8n", {"precision": 0.8, "recall": 0.7, "mAP50": 0.75, "mAP50_95": 0.5})
    _write_exp(tmp_path, "b", "yolov8s", {"mAP50": 0.8})
    (tmp_path / "notes.json").write_text("{}")

    table = build_comparison_table(str(tmp_path))

    assert [r["model"] for r in table] == ["yolov8n", "yolov8s"]
    assert table[0]["mAP50"] == 0.75
    assert table[0]["epochs"] == 42
    assert table[1]["recall"] == "-"


def test_failed_run_without_metrics_shows_dashes(tmp_path):
    _write_exp(tmp_path, "c", "yolonas_s", {"error": "super-gradients not installed"}, status="failed")
    row = build_comparison_table(str(tmp_path))[0]
    assert row["mAP50"] == "-" and row["status"] == "failed"


def test_markdown_has_one_row_per_model(tmp_path):
    _write_exp(tmp_path, "a", "yolov8n", {"mAP50": 0.75})
    md = format_comparison_markdown(build_comparison_table(str(tmp_path)))
    lines = md.splitlines()
    assert len(lines) == 3
    assert lines[2].startswith("| yolov8n |") and "| 120 |" in lines[2]


def test_markdown_empty():
    assert format_comparison_markdown([]) == "No experiments found."
