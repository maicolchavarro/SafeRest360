"""Local (CPU) pipeline: COCO val2017 persons -> YOLO dataset -> fine-tune -> uniform test-split evaluation.

Usage (from vision-engine/, with .venv active):
    python train_local.py prepare
    python train_local.py time-epoch --variant yolov8n --imgsz 416 --no-offline-aug
    python train_local.py train --variants yolov8n --epochs 15 --imgsz 416 --no-offline-aug
    python train_local.py evaluate
"""

import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

DATA = Path("data")
PERSON_DIR = DATA / "person_dataset"
YOLO_DIR = DATA / "person_yolo"
YAML = YOLO_DIR / "dataset.yaml"
YAML_NOAUG = YOLO_DIR / "dataset_noaug.yaml"
EXP_DIR = Path("experiments")
RUNS = Path("runs/train")
RESULTS = EXP_DIR / "eval_results.json"


def prepare(max_images: int, augment_copies: int) -> None:
    from src.dataset.augmentation import augment_dataset
    from src.dataset.coco_extractor import create_dataset_yaml, extract_person_subset
    from src.dataset.splitter import split_dataset

    if YAML.exists():
        print(f"Dataset ya preparado en {YOLO_DIR}; borra esa carpeta para regenerarlo.")
    else:
        stats = extract_person_subset(
            annotations_path=DATA / "annotations" / "instances_val2017.json",
            images_dir=DATA / "val2017",
            output_dir=PERSON_DIR,
            max_images=max_images,
        )
        print("Extracción:", stats)
        print("Split:", split_dataset(PERSON_DIR, YOLO_DIR, 0.7, 0.2, 0.1, seed=42))
        create_dataset_yaml(YOLO_DIR)
        added = augment_dataset(YOLO_DIR / "train", YOLO_DIR / "train", augmentations_per_image=augment_copies)
        print(f"Aumentación: {added} imágenes nuevas en train")

    # Ultralytics already augments online (mosaic, flips, HSV, scale); the offline copies
    # triple CPU epoch time, so this variant trains on the original images only.
    originals = sorted(p.resolve() for p in (YOLO_DIR / "train" / "images").glob("*.jpg") if "_aug" not in p.stem)
    (YOLO_DIR / "train_original.txt").write_text("\n".join(str(p) for p in originals) + "\n")
    YAML_NOAUG.write_text(
        YAML.read_text().replace("train: train/images", "train: train_original.txt")
    )
    print(f"Variante sin aumentación offline: {len(originals)} imágenes de train -> {YAML_NOAUG}")


def _dataset(args) -> str:
    return str(YAML_NOAUG if args.no_offline_aug else YAML)


def _overrides(args) -> dict:
    return dict(
        device="cpu",
        imgsz=args.imgsz,
        batch_size=args.batch,
        workers=args.workers,
        patience=args.patience,
        project=str(RUNS),
    )


def time_epoch(args) -> None:
    from src.training.trainer import run_experiment

    start = time.time()
    run_experiment(
        args.variant, _dataset(args), output_dir=str(EXP_DIR / "timing"), epochs=1,
        name=f"{args.variant}_timing", **_overrides(args),
    )
    print(f"\n1 época de {args.variant} a {args.imgsz}px: {(time.time() - start) / 60:.1f} min")


def train(args) -> None:
    from src.training.trainer import run_experiment

    for variant in args.variants:
        print(f"\n{'=' * 60}\nEntrenando {variant} ({args.epochs} épocas máx, {args.imgsz}px)\n{'=' * 60}")
        record = run_experiment(
            variant, _dataset(args), output_dir=str(EXP_DIR), epochs=args.epochs,
            name=f"{variant}_person_{args.imgsz}", **_overrides(args),
        )
        print(f"{variant}: {record.status}, {record.epochs_completed} épocas, val {record.metrics}")


def _candidates() -> list[dict]:
    models = [
        {"label": "YOLOv8n COCO preentrenado", "kind": "yolo", "weights": "yolov8n.pt", "imgsz": 640,
         "license": "AGPL-3.0", "transfer_learning": False},
        {"label": "YOLOv8s COCO preentrenado", "kind": "yolo", "weights": "yolov8s.pt", "imgsz": 640,
         "license": "AGPL-3.0", "transfer_learning": False},
        {"label": "YOLOv8m COCO preentrenado", "kind": "yolo", "weights": "yolov8m.pt", "imgsz": 640,
         "license": "AGPL-3.0", "transfer_learning": False},
        {"label": "RF-DETR Nano COCO preentrenado", "kind": "rfdetr", "size": "nano", "imgsz": 384,
         "license": "Apache-2.0", "transfer_learning": False},
        {"label": "RF-DETR Small COCO preentrenado", "kind": "rfdetr", "size": "small", "imgsz": 512,
         "license": "Apache-2.0", "transfer_learning": False},
    ]
    for exp in sorted(EXP_DIR.glob("exp_*.json")):
        data = json.loads(exp.read_text())
        if data.get("status") != "completed" or not data.get("weights_path"):
            continue
        variant, imgsz = data["model_variant"], data["config"]["imgsz"]
        name = variant.replace("yolov8", "YOLOv8")
        if imgsz != 640:
            models.append({"label": f"{name} COCO preentrenado ({imgsz}px)",
                           "kind": "yolo", "weights": f"{variant}.pt", "imgsz": imgsz,
                           "license": "AGPL-3.0", "transfer_learning": False})
        models.append({"label": f"{name} ajustado con TL "
                                f"({data['epochs_completed']} ép., {imgsz}px)",
                       "kind": "yolo", "weights": data["weights_path"], "imgsz": imgsz,
                       "license": "AGPL-3.0", "transfer_learning": True, "experiment_id": data["experiment_id"]})
    return models


def evaluate_all(args) -> None:
    from src.evaluation.person_eval import evaluate, load_split, rfdetr_predictor, yolo_predictor

    samples = load_split(YOLO_DIR / "test")
    EXP_DIR.mkdir(exist_ok=True)
    store = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else {"results": {}}
    store.update({
        "split": "test", "dataset_dir": str(YOLO_DIR / "test"), "n_images": len(samples),
        "hardware": f"{platform.processor()} | CPU, sin GPU",
        "method": "pycocotools COCOeval (bbox) + P/R a umbral 0.5 con IoU>=0.5; latencia media en 50 imágenes",
    })

    for m in _candidates():
        if m["label"] in store["results"] and not args.force:
            print(f"Ya evaluado: {m['label']}")
            continue
        if args.only and not any(o.lower() in m["label"].lower() for o in args.only):
            continue
        print(f"\nEvaluando {m['label']} ...")
        predict = (yolo_predictor(m["weights"], imgsz=m["imgsz"]) if m["kind"] == "yolo"
                   else rfdetr_predictor(m["size"]))
        res = evaluate(predict, samples, op_threshold=0.5)
        store["results"][m["label"]] = {**m, **res, "evaluated_at": datetime.now(timezone.utc).isoformat()}
        RESULTS.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  mAP50={res['mAP50']:.3f} mAP50-95={res['mAP50_95']:.3f} P={res['precision']:.3f} "
              f"R={res['recall']:.3f} {res['latency_ms_mean']:.0f} ms")

    lines = [
        "| Modelo | Licencia | Entrada | mAP@50 | mAP@50-95 | Precisión @0.5 | Recall @0.5 | Latencia CPU (ms) | FPS |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in store["results"].values():
        lines.append(
            f"| {r['label']} | {r['license']} | {r['imgsz']}px | {r['mAP50']:.3f} | {r['mAP50_95']:.3f} | "
            f"{r['precision']:.3f} | {r['recall']:.3f} | {r['latency_ms_mean']:.0f} | {r['fps']:.1f} |"
        )
    (EXP_DIR / "eval_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + "\n".join(lines))


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("prepare")
    sp.add_argument("--max-images", type=int, default=2000)
    sp.add_argument("--augment-copies", type=int, default=2)

    for name in ("time-epoch", "train"):
        s = sub.add_parser(name)
        s.add_argument("--imgsz", type=int, default=640)
        s.add_argument("--batch", type=int, default=8)
        s.add_argument("--workers", type=int, default=2)
        s.add_argument("--patience", type=int, default=10)
        s.add_argument("--no-offline-aug", action="store_true")
        if name == "time-epoch":
            s.add_argument("--variant", default="yolov8n")
        else:
            s.add_argument("--variants", nargs="+", default=["yolov8n"])
            s.add_argument("--epochs", type=int, default=15)

    se = sub.add_parser("evaluate")
    se.add_argument("--only", nargs="*", help="evaluar solo modelos cuyo nombre contenga estos textos")
    se.add_argument("--force", action="store_true", help="re-evaluar modelos ya evaluados")

    args = p.parse_args()
    if args.cmd == "prepare":
        prepare(args.max_images, args.augment_copies)
    else:
        {"time-epoch": time_epoch, "train": train, "evaluate": evaluate_all}[args.cmd](args)


if __name__ == "__main__":
    main()
