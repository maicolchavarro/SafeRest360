"""Evaluation metrics computation for object detection models."""


def evaluate_model(
    weights_path: str,
    dataset_yaml: str,
    device: str = "cpu",
    split: str = "test",
) -> dict:
    """Evaluate a YOLO model and return standard metrics.

    Returns:
        Dict with precision, recall, mAP50, mAP50_95, f1
    """
    from ultralytics import YOLO

    model = YOLO(weights_path)
    results = model.val(data=dataset_yaml, device=device, split=split, verbose=False)

    rd = results.results_dict
    precision = rd.get("metrics/precision(B)", 0)
    recall = rd.get("metrics/recall(B)", 0)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "mAP50": round(float(rd.get("metrics/mAP50(B)", 0)), 4),
        "mAP50_95": round(float(rd.get("metrics/mAP50-95(B)", 0)), 4),
        "f1": round(float(f1), 4),
    }
