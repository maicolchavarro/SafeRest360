"""
SafeRest360 — Demo de detección de personas con YOLOv8 + Supervision
Usa el modelo pretrained YOLOv8n (COCO) para detectar personas.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import supervision as sv
from ultralytics import YOLO

OUTPUT_DIR = Path(__file__).parent / "demo_output"
OUTPUT_DIR.mkdir(exist_ok=True)

PERSON_CLASS_ID = 0  # COCO class 0 = person


def create_sample_scene() -> np.ndarray:
    """Create a synthetic restaurant scene with colored rectangles as 'people'."""
    img = np.ones((640, 960, 3), dtype=np.uint8) * 200  # light gray bg

    # Floor
    cv2.rectangle(img, (0, 400), (960, 640), (180, 170, 160), -1)

    # Tables
    cv2.rectangle(img, (100, 300), (300, 400), (80, 60, 40), -1)
    cv2.rectangle(img, (400, 300), (600, 400), (80, 60, 40), -1)
    cv2.rectangle(img, (700, 300), (900, 400), (80, 60, 40), -1)

    # "People" shapes (standing figures)
    for x, color in [(150, (50, 80, 200)), (500, (200, 50, 50)), (800, (50, 180, 50))]:
        # Head
        cv2.circle(img, (x, 220), 20, color, -1)
        # Body
        cv2.rectangle(img, (x - 15, 240), (x + 15, 340), color, -1)
        # Legs
        cv2.line(img, (x - 10, 340), (x - 15, 400), color, 4)
        cv2.line(img, (x + 10, 340), (x + 15, 400), color, 4)

    cv2.putText(img, "SafeRest360 - Escena de prueba", (250, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (60, 60, 60), 2)

    return img


def run_detection_on_image(model: YOLO, image: np.ndarray, conf: float = 0.25):
    """Run YOLO detection and filter to persons only."""
    results = model(image, conf=conf, verbose=False)[0]

    detections = sv.Detections.from_ultralytics(results)
    person_mask = detections.class_id == PERSON_CLASS_ID
    person_detections = detections[person_mask]

    return person_detections, results


def annotate_image(image: np.ndarray, detections: sv.Detections) -> np.ndarray:
    """Annotate image with bounding boxes and labels using supervision."""
    box_annotator = sv.BoxAnnotator(thickness=2)
    label_annotator = sv.LabelAnnotator(text_scale=0.5, text_padding=5)

    labels = [
        f"Persona #{i+1} ({det_conf:.0%})"
        for i, det_conf in enumerate(detections.confidence)
    ]

    annotated = box_annotator.annotate(scene=image.copy(), detections=detections)
    annotated = label_annotator.annotate(scene=annotated, detections=detections, labels=labels)

    return annotated


def main():
    print("=" * 60)
    print("SafeRest360 — Demo de Detección con YOLOv8 + Supervision")
    print("=" * 60)

    # Load model
    print("\n[1/4] Cargando modelo YOLOv8n (pretrained COCO)...")
    model = YOLO("yolov8n.pt")
    print(f"  Modelo cargado: {model.model_name}")
    print(f"  Clases disponibles: {len(model.names)}")
    print(f"  Clase persona: {model.names[PERSON_CLASS_ID]}")

    # Check for user-provided image or use synthetic
    if len(sys.argv) > 1:
        image_path = Path(sys.argv[1])
        if image_path.exists():
            print(f"\n[2/4] Cargando imagen: {image_path}")
            image = cv2.imread(str(image_path))
        else:
            print(f"  Archivo no encontrado: {image_path}")
            print("  Usando escena sintética...")
            image = create_sample_scene()
    else:
        print("\n[2/4] Creando escena de prueba sintética...")
        print("  (Pasa una imagen como argumento: python demo_detection.py imagen.jpg)")
        image = create_sample_scene()

    print(f"  Resolución: {image.shape[1]}x{image.shape[0]}")

    # Run detection
    print("\n[3/4] Ejecutando detección de personas...")
    detections, raw_results = run_detection_on_image(model, image)

    print(f"  Detecciones totales: {len(sv.Detections.from_ultralytics(raw_results))}")
    print(f"  Personas detectadas: {len(detections)}")

    if len(detections) > 0:
        for i, (bbox, conf) in enumerate(zip(detections.xyxy, detections.confidence)):
            x1, y1, x2, y2 = bbox.astype(int)
            print(f"    Persona #{i+1}: [{x1},{y1},{x2},{y2}] confianza={conf:.2%}")
    else:
        print("  (No se detectaron personas — normal con escena sintética)")
        print("  Prueba con una foto real: python demo_detection.py foto.jpg")

    # Annotate and save
    print("\n[4/4] Generando imagen anotada...")
    annotated = annotate_image(image, detections)

    output_path = OUTPUT_DIR / "deteccion_resultado.jpg"
    cv2.imwrite(str(output_path), annotated)
    print(f"  Guardado en: {output_path}")

    # Save original too for comparison
    original_path = OUTPUT_DIR / "original.jpg"
    cv2.imwrite(str(original_path), image)

    # Summary
    print("\n" + "=" * 60)
    print("RESUMEN")
    print(f"  Modelo: YOLOv8n (COCO pretrained)")
    print(f"  Supervision: v{sv.__version__}")
    print(f"  Personas detectadas: {len(detections)}")
    print(f"  Resultados en: {OUTPUT_DIR}")
    print("=" * 60)

    if len(detections) == 0:
        print("\nPara una prueba real, descarga una imagen con personas y ejecuta:")
        print(f"  python {Path(__file__).name} ruta/a/imagen.jpg")

    print("\nPróximo paso: Entrenar modelo personalizado en Google Colab")
    print("  Abre: colab/SafeRest360_Training.ipynb")


if __name__ == "__main__":
    main()
