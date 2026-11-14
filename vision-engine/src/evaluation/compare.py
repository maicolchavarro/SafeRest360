"""Cross-model comparison utilities."""

import json
from pathlib import Path


def build_comparison_table(experiment_dir: str = "experiments") -> list[dict]:
    """Load experiment records and build a comparison table.

    Returns:
        List of dicts, one per model, with metrics and benchmark data.
    """
    experiments = []
    for f in sorted(Path(experiment_dir).glob("exp_*.json")):
        data = json.loads(f.read_text())
        experiments.append(data)

    table = []
    for exp in experiments:
        metrics = exp.get("metrics", {})
        row = {
            "model": exp.get("model_variant", ""),
            "precision": metrics.get("precision", "-"),
            "recall": metrics.get("recall", "-"),
            "mAP50": metrics.get("mAP50", "-"),
            "mAP50_95": metrics.get("mAP50_95", "-"),
            "f1": metrics.get("f1", "-"),
            "duration_s": exp.get("duration_seconds", 0),
            "epochs": exp.get("epochs_completed", 0),
            "status": exp.get("status", ""),
        }
        table.append(row)

    return table


def format_comparison_markdown(table: list[dict]) -> str:
    """Format comparison table as Markdown."""
    if not table:
        return "No experiments found."

    header = "| Model | Precision | Recall | mAP50 | mAP50-95 | F1 | Duration(s) | Status |"
    sep = "|---|---|---|---|---|---|---|---|"
    rows = []
    for r in table:
        rows.append(
            f"| {r['model']} | {r['precision']} | {r['recall']} | "
            f"{r['mAP50']} | {r['mAP50_95']} | {r['f1']} | "
            f"{r['duration_s']:.0f} | {r['status']} |"
        )
    return "\n".join([header, sep] + rows)


LICENSE_INFO = {
    "yolov8n": {"license": "AGPL-3.0", "source": "Ultralytics", "commercial": "Requires Enterprise license for closed-source SaaS"},
    "yolov8s": {"license": "AGPL-3.0", "source": "Ultralytics", "commercial": "Requires Enterprise license for closed-source SaaS"},
    "yolov8m": {"license": "AGPL-3.0", "source": "Ultralytics", "commercial": "Requires Enterprise license for closed-source SaaS"},
    "yolonas_s": {"license": "Apache-2.0", "source": "Deci AI (super-gradients)", "commercial": "Free for commercial use"},
}
