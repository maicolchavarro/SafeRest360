# Modelo de IA: detección de personas

SafeRest360 usa un modelo de visión por computador **solo para encontrar personas** en cada imagen de la cámara. No identifica a nadie y no usa reconocimiento facial. La decisión de avisar la toman reglas programadas por zona, horario y tiempo (`vision-engine/src/rules/`), y la decisión final sobre cada alerta la toma una persona.

## 1. Modelo elegido

| | |
|---|---|
| Modelo | **YOLOv8n** ("YOLO versión ocho, tamaño nano"), preentrenado en COCO |
| Autor y licencia | Ultralytics · AGPL-3.0 |
| Clase usada | `person` (clase 0 de COCO) |
| Entrada | 640 px |
| Seguimiento | ByteTrack (librería `supervision`), para mantener la identidad de cada detección entre imágenes |
| Hardware objetivo | Portátil o miniPC sin tarjeta gráfica (solo CPU) |

Se usa **sin reentrenar**, tal como lo publica Ultralytics (ver la sección 5).

## 2. Dataset de evaluación

Para comparar modelos de forma justa se armó un conjunto propio de personas a partir de **COCO val2017**. Los modelos preentrenados de COCO se entrenan con `train2017`, así que estas imágenes no las vieron durante su entrenamiento.

| Paso | Detalle | Código |
|---|---|---|
| Extracción | Imágenes de COCO val2017 que contienen personas; se descartan las anotaciones de multitud (`iscrowd = 1`) y se convierten al formato YOLO | `src/dataset/coco_extractor.py` |
| Tamaño | 2.000 imágenes | `train_local.py prepare --max-images 2000` |
| División | **70 % entrenamiento / 20 % validación / 10 % prueba** = 1.400 / 400 / 200 imágenes, aleatoria con semilla fija (`seed = 42`) para que sea reproducible | `src/dataset/splitter.py` |
| Conjunto de prueba | 200 imágenes con **775 personas** etiquetadas; solo se usa para la evaluación final | `experiments/eval_results.json` |
| Aumento de datos (opcional) | Volteo horizontal, brillo y contraste, ruido, desenfoque de movimiento, escala y desenfoque gaussiano, solo sobre el conjunto de entrenamiento | `src/dataset/augmentation.py` |

## 3. Métricas y protocolo

Todos los modelos se evalúan con **el mismo código** (`src/evaluation/person_eval.py`) sobre el mismo conjunto de prueba:

- **mAP@50 y mAP@50-95**: calculados con `pycocotools` (protocolo oficial de COCO). Miden qué tan bien encuentra a las personas, de 0 a 1.
- **Precisión y recall @0,5**: con confianza mínima 0,5 y emparejamiento voraz con IoU ≥ 0,5. La precisión indica cuántas detecciones son correctas; el recall, cuántas personas reales se encontraron.
- **Latencia y FPS en CPU**: promedio sobre 50 imágenes, después de 5 imágenes de calentamiento, en un AMD Ryzen 7 5700U. Es el tiempo del modelo con **una imagen a la vez**.

## 4. Resultados (conjunto de prueba: 200 imágenes, 775 personas)

| Modelo | Licencia | Entrada | mAP@50 | mAP@50-95 | Precisión | Recall | FPS CPU |
|---|---|---|---|---|---|---|---|
| **YOLOv8n preentrenado** | AGPL-3.0 | 640 px | **0,736** | 0,483 | 0,936 | 0,475 | **20,1** |
| YOLOv8s preentrenado | AGPL-3.0 | 640 px | 0,792 | 0,555 | 0,917 | 0,587 | 10,1 |
| YOLOv8m preentrenado | AGPL-3.0 | 640 px | 0,819 | 0,588 | 0,897 | 0,663 | 3,3 |
| RF-DETR Nano preentrenado | Apache-2.0 | 384 px | 0,782 | 0,527 | 0,904 | 0,609 | 4,8 |
| RF-DETR Small preentrenado | Apache-2.0 | 512 px | 0,832 | 0,589 | 0,903 | 0,676 | 2,6 |
| YOLOv8n preentrenado | AGPL-3.0 | 416 px | 0,655 | 0,420 | 0,956 | 0,395 | 27,2 |
| YOLOv8n ajustado (15 épocas) | AGPL-3.0 | 416 px | 0,578 | 0,339 | 0,916 | 0,339 | 26,5 |

Fuente: [`vision-engine/experiments/eval_results.md`](../vision-engine/experiments/eval_results.md) y `eval_results.json`.

## 5. Decisión técnica

- **Por qué YOLOv8n:** es el único modelo que supera 15 imágenes por segundo en CPU. Los más precisos (YOLOv8m y RF-DETR Small) son entre 6 y 8 veces más lentos, y un restaurante pequeño no va a comprar un computador con tarjeta gráfica. Ninguna configuración cumple a la vez mAP@50 ≥ 0,80 y ≥ 15 FPS.
- **Por qué no se reentrenó:** se ajustó YOLOv8n con transferencia de aprendizaje (15 épocas, 416 px, AdamW, `lr0 = 0,001`, semilla 42, 1 h en CPU) y el mAP@50 en prueba **bajó** de 0,655 a 0,578 frente al mismo modelo sin ajustar. Con pocas imágenes y solo CPU, el ajuste empeoró el modelo, así que se conserva el preentrenado. Registro del experimento: `experiments/exp_yolov8n_20261115_020114_f55bee.json` y la curva por época en `experiments/yolov8n_person_416_results.csv`.
- **Plan B por licencia:** si el servicio se ofrece con código cerrado, la AGPL-3.0 obliga a publicar el código o a comprar una licencia a Ultralytics. La alternativa evaluada es **RF-DETR** (Apache-2.0), que es más precisa pero más lenta.

## 6. Limitaciones conocidas

- **COCO no es un restaurante.** Las imágenes de prueba no son de cámaras de seguridad en cocinas, bodegas o cajas. El desempeño real se debe medir en el piloto.
- **Recall de 0,475 por imagen.** En una sola imagen el modelo no encuentra a cerca de la mitad de las personas, sobre todo las pequeñas o tapadas. Como la regla espera una confirmación de 2 segundos y analiza muchas imágenes en ese tiempo, se espera que la persona se detecte en alguna, pero **esto no está medido todavía**.
- **20 FPS no garantizan varias cámaras.** La cifra mide solo el modelo con una imagen a la vez; no incluye recibir y decodificar el video de 2 a 4 cámaras simultáneas.
- **Sin pruebas de noche, oclusión ni ataques adversarios.** Quedan para el piloto.

## 7. Evaluación propuesta en el piloto

| | |
|---|---|
| Duración | 7 días (168 h de video) con 2 a 4 cámaras |
| Unidad de análisis | El evento (presencia en zona, zona sin personal, aforo), no la imagen |
| Referencia | Revisión manual del video por dos personas |
| Condiciones | Día, noche, hora pico y personas tapadas |
| Criterio de aprobación | Detectar al menos 9 de cada 10 eventos reales y máximo 3 falsas alarmas por cámara al día |

## 8. Cómo reproducir

```bash
cd vision-engine
python train_local.py prepare                       # COCO val2017 → 2.000 imágenes → 1.400/400/200
python train_local.py train --variants yolov8n --epochs 15 --imgsz 416 --no-offline-aug
python train_local.py evaluate                      # compara todos los modelos en el conjunto de prueba
```

Requiere descargar COCO val2017 y sus anotaciones en `vision-engine/data/` (ver el README principal). El entrenamiento con GPU está en `colab/SafeRest360_Training.ipynb`.
