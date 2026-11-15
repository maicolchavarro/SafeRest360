"""Framework-independent person-detection evaluation on a YOLO-format split.

Every model is scored by the same code: COCO mAP via pycocotools, plus precision/recall
at a fixed operating threshold (IoU >= 0.5, greedy matching), plus CPU latency.
"""

import time
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image

# image path -> (N, 5) array of [x1, y1, x2, y2, score] in pixels, persons only
Predictor = Callable[[Path, float], np.ndarray]


def load_split(split_dir: Path) -> list[dict]:
    samples = []
    for img_path in sorted((split_dir / "images").glob("*.jpg")):
        w, h = Image.open(img_path).size
        boxes = []
        label = split_dir / "labels" / f"{img_path.stem}.txt"
        if label.exists():
            for line in label.read_text().split("\n"):
                if line.strip():
                    _, xc, yc, bw, bh = (float(v) for v in line.split()[:5])
                    boxes.append([(xc - bw / 2) * w, (yc - bh / 2) * h, (xc + bw / 2) * w, (yc + bh / 2) * h])
        samples.append({"path": img_path, "width": w, "height": h, "boxes": np.array(boxes).reshape(-1, 4)})
    return samples


def _iou(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area = (box[2] - box[0]) * (box[3] - box[1])
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    return inter / (area + areas - inter + 1e-9)


def precision_recall_at(samples: list[dict], preds: list[np.ndarray], threshold: float) -> dict:
    tp = fp = 0
    n_gt = sum(len(s["boxes"]) for s in samples)
    for s, p in zip(samples, preds):
        p = p[p[:, 4] >= threshold]
        p = p[np.argsort(-p[:, 4])]
        matched = np.zeros(len(s["boxes"]), dtype=bool)
        for det in p:
            if len(s["boxes"]) == 0:
                fp += 1
                continue
            ious = _iou(det[:4], s["boxes"])
            ious[matched] = -1
            j = int(np.argmax(ious))
            if ious[j] >= 0.5:
                matched[j] = True
                tp += 1
            else:
                fp += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / n_gt if n_gt else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": n_gt - tp}


def coco_map(samples: list[dict], preds: list[np.ndarray]) -> dict:
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval

    images, anns, dets = [], [], []
    for i, (s, p) in enumerate(zip(samples, preds)):
        images.append({"id": i, "width": s["width"], "height": s["height"]})
        for b in s["boxes"]:
            w, h = b[2] - b[0], b[3] - b[1]
            anns.append({"id": len(anns) + 1, "image_id": i, "category_id": 1,
                         "bbox": [float(b[0]), float(b[1]), float(w), float(h)], "area": float(w * h), "iscrowd": 0})
        for d in p:
            dets.append({"image_id": i, "category_id": 1, "score": float(d[4]),
                         "bbox": [float(d[0]), float(d[1]), float(d[2] - d[0]), float(d[3] - d[1])]})
    if not dets:
        return {"mAP50": 0.0, "mAP50_95": 0.0}

    gt = COCO()
    gt.dataset = {"images": images, "annotations": anns, "categories": [{"id": 1, "name": "person"}]}
    gt.createIndex()
    ev = COCOeval(gt, gt.loadRes(dets), "bbox")
    ev.evaluate()
    ev.accumulate()
    ev.summarize()
    return {"mAP50_95": float(ev.stats[0]), "mAP50": float(ev.stats[1])}


def evaluate(predict: Predictor, samples: list[dict], op_threshold: float = 0.5,
             latency_images: int = 50, warmup: int = 5) -> dict:
    preds = [predict(s["path"], 0.001) for s in samples]
    result = coco_map(samples, preds)
    result.update(precision_recall_at(samples, preds, op_threshold))
    result["op_threshold"] = op_threshold

    subset = samples[:latency_images]
    for s in subset[:warmup]:
        predict(s["path"], op_threshold)
    times = []
    for s in subset:
        t = time.perf_counter()
        predict(s["path"], op_threshold)
        times.append((time.perf_counter() - t) * 1000)
    result["latency_ms_mean"] = float(np.mean(times))
    result["latency_ms_p95"] = float(np.percentile(times, 95))
    result["fps"] = 1000.0 / result["latency_ms_mean"]
    result["n_images"] = len(samples)
    result["n_persons"] = int(sum(len(s["boxes"]) for s in samples))
    return result


def yolo_predictor(weights: str, imgsz: int = 640, person_class: int = 0) -> Predictor:
    from ultralytics import YOLO

    model = YOLO(weights)

    def predict(path: Path, conf: float) -> np.ndarray:
        r = model.predict(str(path), conf=conf, classes=[person_class], imgsz=imgsz,
                          device="cpu", max_det=300, verbose=False)[0]
        b = r.boxes
        return np.hstack([b.xyxy.numpy(), b.conf.numpy()[:, None]]) if len(b) else np.zeros((0, 5))

    return predict


def rfdetr_predictor(size: str) -> Predictor:
    import rfdetr

    model = {"nano": rfdetr.RFDETRNano, "small": rfdetr.RFDETRSmall, "medium": rfdetr.RFDETRMedium}[size](device="cpu")
    predictor = model.inference()
    person_id = 1  # RF-DETR keeps the original COCO category ids

    def predict(path: Path, conf: float) -> np.ndarray:
        d = predictor.predict(Image.open(path).convert("RGB"), threshold=conf)
        keep = d.class_id == person_id
        return np.hstack([d.xyxy[keep], d.confidence[keep][:, None]]) if keep.any() else np.zeros((0, 5))

    return predict
