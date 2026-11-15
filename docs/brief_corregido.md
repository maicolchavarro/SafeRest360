# SafeRest360: Brief de Negocio Corregido — AI Pitch 2026

**Universidad de Boyacá — Ingeniería de Sistemas — Inteligencia Artificial — Noviembre 2026**

---

## A. Resumen Ejecutivo

SafeRest360 es una plataforma SaaS de videovigilancia inteligente para restaurantes que utiliza modelos YOLO con Transfer Learning para detectar personas en tiempo real, evaluar reglas de zona configurables, y notificar al administrador vía WhatsApp. El sistema aprovecha las cámaras existentes del restaurante, no requiere hardware adicional y se instala en una sola visita.

**Diferenciadores clave:**
- Aprovecha cámaras IP existentes (no requiere inversión adicional en hardware)
- Alertas configurables por zona, horario y tipo de evento
- Notificaciones inmediatas por WhatsApp (canal ya adoptado por el mercado objetivo)
- Costo significativamente menor que un vigilante o plataformas internacionales

---

## B. El Problema y Contexto de Mercado

El administrador de un restaurante no puede estar en todas partes al mismo tiempo. Las cámaras graban continuamente, pero casi nadie las revisa en tiempo real. Problemas como accesos no autorizados a la bodega, ausencia del cajero, o presencia en zonas restringidas pasan desapercibidos hasta que es demasiado tarde.

**Tamaño del mercado:** En Colombia hay aproximadamente 132.000 restaurantes y negocios de comida, de los cuales 54.100 son formales (Fuente: DANE, Encuesta Anual de Servicios 2023). Los gremios del sector han identificado la inseguridad como una de las principales preocupaciones operativas.

**Mercado objetivo inicial:** Restaurantes pequeños y medianos en Tunja y Boyacá con 2-8 cámaras instaladas, expandiendo luego a otras ciudades intermedias.

---

## C. La Solución: Pipeline de 5 Pasos

El sistema funciona en cinco pasos:

1. **Conexión**: Se conecta a las cámaras IP existentes del restaurante mediante protocolo RTSP/ONVIF.
2. **Detección**: Un modelo de IA (YOLO) analiza los frames extraídos varias veces por segundo y detecta personas.
3. **Seguimiento**: ByteTrack asigna identidades persistentes a cada persona detectada entre frames.
4. **Evaluación de reglas**: El motor de reglas verifica si alguna persona viola una zona configurada (entrada a zona restringida, abandono de zona monitoreada, superación de aforo máximo).
5. **Notificación**: Si se genera una alerta, el administrador recibe un mensaje de WhatsApp con la descripción, zona, cámara, hora y snapshot.

---

## D. Arquitectura del Sistema

> **[Observación del jurado #1: Arquitectura cloud]**

### Arquitectura de componentes (C4 — Nivel 2)

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                     │
│  Dashboard │ Cámaras │ Zonas │ Alertas │ Configuración   │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS / JWT
┌──────────────────────▼──────────────────────────────────┐
│                   BACKEND (FastAPI)                       │
│  Auth │ CRUD │ Alert Service │ Notification Dispatch      │
│                       │                                   │
│  ┌────────────────────▼────────────────────────────┐     │
│  │           VISION ENGINE (in-process / gRPC)      │     │
│  │  Detector (YOLO) → Tracker (ByteTrack) → Rules   │     │
│  └──────────────────────────────────────────────────┘     │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              BASE DE DATOS (PostgreSQL)                   │
│  restaurants │ users │ cameras │ zones │ rules │ alerts   │
│  notifications │ model_registry                           │
└─────────────────────────────────────────────────────────┘
```

### Flujo de datos

1. El **Camera Connector** extrae frames del stream RTSP de cada cámara.
2. Los frames pasan al **Vision Engine** que ejecuta detección + tracking + evaluación de reglas.
3. Los **eventos** generados se persisten como alertas en PostgreSQL.
4. El **Notification Service** despacha alertas a WhatsApp Business API.
5. El **Frontend** consulta el API REST para mostrar dashboard, alertas y configuración.

### Despliegue en la nube (producción)

Para producción, la arquitectura se despliega en contenedores Docker orquestados:

| Servicio | Recurso | Justificación |
|----------|---------|---------------|
| Frontend | Vercel / CDN estático | Contenido estático, bajo costo |
| Backend API | AWS ECS / Cloud Run | Auto-scaling por demanda |
| Vision Engine | GPU instance (T4) | Inferencia YOLO requiere GPU |
| Base de datos | RDS PostgreSQL / Cloud SQL | Managed DB, backups automáticos |
| Almacenamiento | S3 / GCS | Snapshots de alertas |
| Cola de mensajes | Redis / SQS | Desacople notificaciones |

---

## E. Cámaras: Compatibilidad y Protocolo Piloto

**Opción 1 — Cámaras existentes**: Antes de la instalación, se realiza un piloto de 3-7 días para validar: accesibilidad del stream RTSP, resolución mínima (720p), iluminación nocturna, ángulo de cobertura de las zonas definidas.

**Opción 2 — Cámaras recomendadas**: Cámaras IP de 4MP con soporte ONVIF, conexión por cable Ethernet (PoE). Precio en Colombia: $450.000–$740.000 COP por unidad.

**Matriz de compatibilidad:**

| Característica | Mínimo | Recomendado |
|---------------|--------|-------------|
| Resolución | 720p (1280×720) | 1080p (1920×1080) |
| Protocolo | RTSP | RTSP + ONVIF |
| Conexión | WiFi o cable | Cable Ethernet (PoE) |
| Visión nocturna | Deseable | Sí (IR) |
| FPS | 10 | 15-25 |

---

## F. Motor de Visión: Selección de Modelo YOLO

> **[Observación del jurado #3: Selección y licenciamiento de YOLO]**

### Familia YOLO: Evolución y contexto

YOLO (You Only Look Once) es una familia de modelos de detección de objetos en tiempo real. Desde YOLOv1 (Redmon et al., 2016) hasta las versiones actuales, la arquitectura ha evolucionado significativamente en precisión y velocidad.

**Variantes evaluadas** (parámetros contados sobre los pesos descargados):

| Modelo | Autor | Licencia código / pesos | Parámetros | Implicación SaaS |
|--------|-------|-------------------------|------------|-------------------|
| YOLOv8n | Ultralytics | AGPL-3.0 / AGPL-3.0 | 3,16 M | SaaS de código cerrado requiere licencia Enterprise de Ultralytics |
| YOLOv8s | Ultralytics | AGPL-3.0 / AGPL-3.0 | 11,17 M | Ídem |
| YOLOv8m | Ultralytics | AGPL-3.0 / AGPL-3.0 | 25,90 M | Ídem |
| RF-DETR Nano | Roboflow | Apache-2.0 / Apache-2.0 | 30,47 M | Uso comercial permitido |
| RF-DETR Small | Roboflow | Apache-2.0 / Apache-2.0 | 32,11 M | Uso comercial permitido |
| YOLO-NAS-S | Deci AI | Apache-2.0 / licencia propia | ~12 M | **Pesos preentrenados no permiten uso comercial** sin acuerdo con Deci |

### Análisis de licencias

La licencia **AGPL-3.0** de Ultralytics exige que un software que use YOLOv8 y se ofrezca como servicio (SaaS) publique su código fuente completo bajo AGPL, o que se adquiera una licencia Enterprise (precio a cotizar con Ultralytics). El repositorio de SafeRest360 es público, por lo que el MVP académico cumple esta condición.

**Corrección respecto a la versión anterior de este Brief:** se había indicado que YOLO-NAS-S era "libre para uso comercial". El código de super-gradients es Apache-2.0, pero los **pesos preentrenados** de YOLO-NAS se distribuyen con una licencia propia de Deci que prohíbe el uso comercial sin un acuerdo aparte (archivo `LICENSE.YOLONAS.md` del repositorio Deci-AI/super-gradients). Además, `super-gradients` no se pudo instalar en el entorno de desarrollo (Windows, Python 3.12). YOLO-NAS queda **descartado**.

**RF-DETR** (Roboflow) es la alternativa con licencia permisiva: los tamaños Nano, Small y Medium tienen código y pesos bajo Apache-2.0, preentrenados en COCO (incluye la clase persona).

**Estrategia**: MVP y validación académica con **YOLOv8n preentrenado** (código publicado, cumple AGPL). Para producción comercial de código cerrado: migrar a **RF-DETR** (Apache-2.0) en una instancia con GPU, o adquirir la licencia Enterprise de Ultralytics. La decisión se sustenta en las mediciones de la sección H.

---

## G. Dataset y Entrenamiento por Transfer Learning

> **[Observaciones del jurado #4 y #5: Transfer Learning y datasets]**

### Dataset: COCO 2017 — Extracción de clase persona

Se utiliza el dataset público **COCO 2017** (Lin et al., 2014): 118K imágenes de entrenamiento (train2017) y 5K de validación (val2017), 80 categorías. **Los datos no fueron recopilados por el equipo**; no se capturaron imágenes de personas en restaurantes.

**Subconjunto usado en los experimentos (ejecutado):**
1. Fuente: **COCO val2017**. Los pesos preentrenados de YOLOv8 y RF-DETR se entrenaron con train2017, así que usar val2017 evita evaluar con imágenes que los modelos ya vieron.
2. Filtrar anotaciones con `category_id == 1` (persona) e `iscrowd == 0`; convertir cajas COCO `[x, y, w, h]` a formato YOLO normalizado.
3. Tomar **2.000 imágenes** con al menos una persona → **7.680 cajas de persona**.
4. División por imagen (no por anotación), `seed=42`: **1.400 train / 400 val / 200 test**. El split de test contiene **775 personas**.

Para un entrenamiento de producción el mismo pipeline (`vision-engine/src/dataset/`) acepta train2017 completo.

### Augmentación de datos

Pipeline offline con Albumentations (MIT), parámetros tal como están en `src/dataset/augmentation.py`:
- HorizontalFlip (p=0,5)
- RandomBrightnessContrast (±0,3; p=0,4)
- GaussNoise (desv. 0,02–0,05; p=0,3)
- MotionBlur (kernel ≤5; p=0,2)
- RandomScale (±20 %; p=0,3)
- GaussianBlur (kernel 3–5; p=0,15)

Genera 2 copias por imagen de train (+2.800 imágenes). En el experimento en CPU se entrenó **solo con las 1.400 originales**, porque Ultralytics ya aplica aumentación en línea en cada época (mosaic, volteo, HSV, escala) y las copias offline triplicaban el tiempo por época.

### Protocolo de Transfer Learning

1. **Preentrenamiento**: pesos COCO completos (80 clases).
2. **Fine-tuning**: reentrenamiento sobre el subconjunto de personas con `single_cls=True`. En YOLOv8n se transfirieron **349 de 355 tensores**; la cabeza de detección se reinicia para 1 clase.
3. **Configuración diseñada (GPU)**: epochs=100, imgsz=640, batch=16, AdamW, lr0=0,001, patience=20.
4. **Configuración ejecutada (CPU local, sin GPU)**: YOLOv8n, **15 épocas**, imgsz=416, batch=8, AdamW, lr0=0,001, patience=10, seed=42. Duración: **59,5 min** en un AMD Ryzen 7 5700U. El intento en Google Colab (GPU T4) no llegó a completarse por desconexiones del runtime.
5. **Trazabilidad**: cada experimento queda en `vision-engine/experiments/exp_*.json` y la curva por época en `vision-engine/experiments/yolov8n_person_416_results.csv`.

El Transfer Learning busca conservar las características aprendidas en COCO (bordes, texturas, formas) y especializar el modelo en personas. La sección H muestra qué tan bien funcionó con el presupuesto de cómputo disponible.

---

## H. Comparación de Modelos y Resultados

> **[Observaciones del jurado #6 y #7: Estado del arte y comparación]**

### Estado del arte en detección de personas

Cifras publicadas por los autores (no medidas por el equipo). Se indica el benchmark porque no son comparables entre sí:

| Referencia | Modelo | Resultado publicado | Benchmark |
|-----------|--------|---------------------|-----------|
| Redmon et al. (2016) | YOLOv1 | 63,4 mAP | PASCAL VOC 2007 |
| Bochkovskiy et al. (2020) | YOLOv4 | 43,5 AP (65,7 AP50) | COCO test-dev |
| Jocher et al. (2023) | YOLOv8x (la variante más grande) | 53,9 mAP50-95 | COCO val2017, 80 clases |
| Deci AI (2023) | YOLO-NAS-L | 52,2 mAP50-95 | COCO val2017, 80 clases |
| Roboflow (2025) | RF-DETR | Detector tipo transformer con backbone DINOv2 | COCO |

### Resultados medidos por el equipo

**Método** (`vision-engine/src/evaluation/person_eval.py`, mismo código para todos los modelos):
- Split de **test**: 200 imágenes de COCO val2017 con **775 personas** (sección G).
- **mAP@50 y mAP@50-95**: `pycocotools` COCOeval, solo clase persona.
- **Precisión, Recall y F1** al **umbral de confianza 0,5** que usa la aplicación, con IoU ≥ 0,5.
- **Latencia**: media por imagen en 50 imágenes, tras 5 de calentamiento, en **CPU AMD Ryzen 7 5700U, sin GPU**. Incluye preprocesamiento y postprocesamiento.
- Datos crudos en `vision-engine/experiments/eval_results.json`.

| Modelo | Licencia | Entrada | mAP@50 | mAP@50-95 | Precisión | Recall | F1 | Latencia CPU | FPS CPU |
|--------|----------|---------|--------|-----------|-----------|--------|----|--------------|---------|
| YOLOv8n preentrenado | AGPL-3.0 | 640 px | 0,736 | 0,483 | 0,936 | 0,475 | 0,630 | 50 ms | 20,1 |
| YOLOv8s preentrenado | AGPL-3.0 | 640 px | 0,792 | 0,555 | 0,917 | 0,587 | 0,716 | 99 ms | 10,1 |
| YOLOv8m preentrenado | AGPL-3.0 | 640 px | 0,819 | 0,588 | 0,897 | 0,663 | 0,763 | 300 ms | 3,3 |
| RF-DETR Nano preentrenado | Apache-2.0 | 384 px | 0,782 | 0,527 | 0,904 | 0,609 | 0,728 | 208 ms | 4,8 |
| RF-DETR Small preentrenado | Apache-2.0 | 512 px | **0,832** | **0,589** | 0,903 | **0,676** | **0,773** | 390 ms | 2,6 |
| YOLOv8n preentrenado | AGPL-3.0 | 416 px | 0,655 | 0,420 | 0,956 | 0,395 | 0,559 | 37 ms | 27,2 |
| YOLOv8n con Transfer Learning (15 épocas) | AGPL-3.0 | 416 px | 0,578 | 0,339 | 0,916 | 0,339 | 0,495 | 38 ms | 26,5 |

### Lectura de los resultados

1. **Pocas falsas alarmas, muchas personas no detectadas.** Al umbral 0,5 todos los modelos tienen precisión entre 0,90 y 0,96, pero recall entre 0,34 y 0,68. Las personas pequeñas o lejanas son la causa principal. Para YOLOv8n a 640 px, el AP por tamaño fue 0,19 en personas pequeñas frente a 0,76 en grandes; para RF-DETR Small, 0,27 frente a 0,86. COCO incluye muchas multitudes y personas lejanas; el rendimiento con cámaras de restaurante debe medirse en el piloto (sección I).
2. **El Transfer Learning corto empeoró el modelo.** El YOLOv8n ajustado obtuvo mAP@50 de 0,578, frente a 0,655 del mismo modelo sin ajustar a 416 px. Causas identificables:
   - la cabeza de detección se reinicia al pasar a 1 clase;
   - solo se usaron 1.400 imágenes y 15 épocas en CPU, frente a las 118K imágenes con que se entrenó el modelo original;
   - el mAP@50 de validación seguía subiendo al terminar (0,438 en la época 1 y 0,602 en la 15), es decir, el modelo quedó subentrenado.

   **Conclusión:** con este presupuesto, el ajuste no supera al modelo preentrenado. Tiene sentido repetirlo con imágenes del dominio (cámaras de restaurante, con consentimiento y aviso según la Ley 1581) y con GPU.
3. **Frente a los umbrales objetivo de la sección I:**
   - mAP@50 ≥ 0,80: lo cumplen YOLOv8m (0,819) y RF-DETR Small (0,832).
   - FPS ≥ 15 en CPU: solo YOLOv8n (20,1 a 640 px).
   - Recall ≥ 0,85: **ningún modelo lo cumple** al umbral 0,5. Queda como pendiente para el piloto.

### Modelo seleccionado

- **MVP y demo: YOLOv8n preentrenado en COCO, 640 px.** Es el único que cumple el requisito de tiempo real en CPU (20 FPS), tiene la mayor precisión a 640 px (0,936) y ya está integrado en el backend. El modelo ajustado **no** se promueve porque es peor.
- **Producción comercial (código cerrado): RF-DETR Small** (Apache-2.0), el más preciso. Requiere GPU o procesar menos cuadros por segundo, porque en CPU da 2,6 FPS. La alternativa es la licencia Enterprise de Ultralytics.
- **Riesgo abierto:** el recall por cuadro es bajo. Que una persona dentro de una zona sea detectada en al menos uno de varios cuadros consecutivos es una hipótesis que **debe verificarse** con video real en el piloto.

---

## I. Protocolo de Evaluación

> **[Observación del jurado #8: Protocolo de evaluación]**

### Métricas de calidad

- **mAP@50**: Precisión media a IoU ≥ 0.50 (métrica principal)
- **mAP@50-95**: Precisión media promediando IoU de 0.50 a 0.95
- **Precision**: TP / (TP + FP)
- **Recall**: TP / (TP + FN)
- **F1**: Media armónica de precision y recall

**Umbrales objetivo:**
- mAP@50 ≥ 0.80 (aceptable para videovigilancia)
- Recall ≥ 0.85 (minimizar personas no detectadas)
- FPS ≥ 15 (procesamiento en pseudo-tiempo real)

### Protocolo de validación en campo

1. **Piloto controlado** (3-7 días): Instalar en 1 restaurante real, 2-4 cámaras.
2. **Horas de video procesadas**: Mínimo 168 horas (1 semana completa, 24/7).
3. **Revisión manual**: Muestreo aleatorio de 200 frames para calcular precision/recall real.
4. **Condiciones variadas**: Día, noche, hora pico, hora valle, iluminación artificial.
5. **Métricas de negocio**: Alertas útiles vs. falsas alarmas, tiempo de respuesta del administrador.

### Evaluación de rendimiento

- **Benchmark ejecutado**: 5 inferencias de calentamiento + 50 imágenes reales del split de test, una por una
- **Métricas**: latencia media, P95 y FPS (`eval_results.json`)
- **Hardware medido**: CPU AMD Ryzen 7 5700U, sin GPU. Una medición en GPU (por ejemplo NVIDIA T4 en la nube) queda pendiente.

---

## J. Reglas, Notificaciones y Falsos Positivos

> **[Observaciones del jurado #9 y #10: Coherencia notificaciones y falsos positivos]**

### Motor de reglas

Tres tipos de reglas configurables por zona:

| Tipo | Trigger | Ejemplo |
|------|---------|---------|
| `no_entry` | Persona detectada en zona restringida | "Persona en bodega" |
| `zone_abandoned` | Ninguna persona en zona monitoreada por N segundos | "Caja sin atender por 2 min" |
| `max_occupancy` | Más de N personas en una zona | "Más de 3 personas en cocina" |

### Mecanismo anti-flood (cooldown)

Cada regla tiene un **cooldown** configurable (por defecto 300 segundos = 5 minutos). Después de generar una alerta, la misma regla no puede generar otra durante el período de cooldown, evitando inundar al administrador con notificaciones repetitivas.

### Coherencia de los 300 avisos/mes

El plan básico incluye 300 notificaciones WhatsApp por mes:
- **Cálculo**: ~10 avisos/día × 30 días = 300
- **Supuestos**: 4 cámaras, 3-4 zonas configuradas, cooldown de 5 min, horario de operación 10-22h
- **Si se excede**: Las alertas se siguen registrando en el dashboard pero no se envían por WhatsApp hasta el siguiente ciclo. Paquetes adicionales disponibles.

### Estrategia contra falsos positivos

1. **Umbral de confianza configurable**: Por defecto 0.5, ajustable por restaurante.
2. **Tracking persistente**: ByteTrack evita contar la misma persona múltiples veces.
3. **Cooldown**: Previene alertas repetidas del mismo evento.
4. **Feedback loop**: El operador marca alertas como "falsa alarma" → métricas para ajustar umbrales.
5. **Calibración inicial**: Durante el piloto de 3-7 días se ajustan zonas y umbrales.
6. **Zona mínima de confianza**: Solo personas cuyo centro de bounding box está dentro del polígono generan alertas (no basta con superposición parcial).

---

## K. Modelo de Negocio y Viabilidad Económica

> **[Observación del jurado #15: Viabilidad económica]**

### Plan de precios

| Plan | Precio/mes (COP) | Cámaras | Alertas WhatsApp | Zonas |
|------|------------------|---------|-------------------|-------|
| Básico | $99.000 | Hasta 4 | 300 | 6 |
| Profesional | $149.000 | Hasta 8 | 600 | 12 |
| Empresa | A convenir | Ilimitadas | Ilimitadas | Ilimitadas |

Equivale a ~US$9/cámara/mes, significativamente menos que plataformas internacionales (US$15-50/cámara) y mucho menos que un vigilante nocturno (~$1.800.000 COP/mes).

### Estructura de costos por restaurante (Plan Profesional, 8 cámaras)

| Concepto | Costo/mes (COP) | Notas |
|----------|-----------------|-------|
| GPU Cloud (inferencia) | $45.000 | T4 compartida, ~4h/día procesamiento |
| WhatsApp Business API | $1.620 | 600 msgs × ~US$0.0009 × TRM 3.000 |
| PostgreSQL hosting | $12.000 | RDS micro, shared |
| Almacenamiento (S3) | $3.000 | ~5 GB snapshots/mes |
| Infraestructura general | $15.000 | Load balancer, DNS, SSL |
| **Total costo variable** | **$76.620** | |
| **Ingreso** | **$149.000** | Plan Profesional |
| **Margen bruto** | **$72.380 (48.6%)** | |

### Escalabilidad de costos

| Escala | Restaurantes | Ingreso mensual | Costo variable | Costo fijo | Margen |
|--------|-------------|-----------------|----------------|------------|--------|
| Piloto | 1 | $149.000 | $76.620 | $500.000 | -$427.620 |
| MVP | 10 | $1.490.000 | $766.200 | $800.000 | -$76.200 |
| Breakeven | ~15 | $2.235.000 | $1.149.300 | $800.000 | $285.700 |
| Escala | 50 | $7.450.000 | $3.831.000 | $1.200.000 | $2.419.000 |

**Punto de equilibrio estimado**: ~15 restaurantes en plan profesional.

---

## L. Reconocimiento Facial: Fase Futura

> **[Observación del jurado #12: Reconocimiento facial como futuro]**

El reconocimiento facial **NO está incluido en el MVP**. Es una funcionalidad planificada para una fase futura que requiere:

### Análisis legal (Ley 1581 de 2012)

La cara de una persona es un **dato biométrico sensible** según la Ley 1581 de 2012 (Ley de Protección de Datos Personales de Colombia):

- **Artículo 5**: Los datos biométricos se clasifican como datos sensibles.
- **Artículo 6**: El tratamiento de datos sensibles requiere **autorización previa, expresa e informada** del titular.
- **SIC (Superintendencia de Industria y Comercio)**: Las disposiciones sobre videovigilancia exigen:
  - Aviso visible de grabación
  - Registro del responsable ante el RNBD (Registro Nacional de Bases de Datos)
  - Política de tratamiento de datos publicada
  - Procedimiento de acceso, rectificación y supresión

### Requisitos para fase futura

1. Consentimiento escrito de cada empleado
2. Almacenamiento de embeddings cifrados (no fotos)
3. Acceso restringido con auditoría
4. Borrado al terminar contrato o solicitud del empleado
5. Validación con abogado especialista en protección de datos
6. **Nunca** aplicable a clientes o visitantes

---

## M. Privacidad y Protección de Datos

> **[Observación del jurado #13: Protección de datos]**

### Principios de diseño

- **Privacy by design**: Los datos se minimizan desde la captura.
- **No se almacenan frames completos**: Solo se guardan snapshots de eventos de alerta.
- **Retención limitada**: Snapshots se eliminan automáticamente a los 30 días.
- **Sin identificación personal**: El MVP detecta "persona", no identidades.

### Medidas técnicas

| Medida | Implementación |
|--------|---------------|
| Cifrado en tránsito | HTTPS/TLS 1.3 para API, RTSP seguro para cámaras |
| Cifrado en reposo | AES-256 para snapshots almacenados |
| Autenticación | JWT con bcrypt, roles (admin/operador) |
| Acceso mínimo | Cada restaurante solo ve sus propios datos |
| Auditoría | Log de acciones con timestamp y usuario |
| Cámaras no expuestas | Las cámaras nunca se conectan directamente a Internet |

### Cumplimiento regulatorio

- **Ley 1581 de 2012**: Política de tratamiento de datos, registro RNBD
- **SIC Videovigilancia**: Aviso de grabación visible, responsable identificado
- **Un aviso es una alerta para revisar, nunca una acusación**: La decisión final siempre la toma una persona

---

## N. Robustez y Casos Límite

> **[Observación del jurado #11: Robustez]**

### Escenarios adversos identificados

| Escenario | Impacto | Mitigación |
|-----------|---------|------------|
| Baja iluminación / noche | Reducción de recall | Visión nocturna IR, augmentación con ajuste de brillo |
| Oclusión parcial | Persona parcialmente visible | Modelo entrenado con oclusiones en COCO |
| Reflejos / espejos | Detección de reflejos como personas | Umbral de confianza + calibración de zonas |
| Cámara movida / desenfocada | Detecciones incorrectas | Monitoreo de calidad de frame, heartbeat |
| Múltiples personas superpuestas | Conteo incorrecto | ByteTrack mantiene tracking por identidad |
| Objetos similares (maniquíes, pósters) | Falsos positivos | Feedback loop + ajuste de umbral |
| Pérdida de conexión de cámara | Sin procesamiento | Alerta de cámara offline, estado "error" |
| Cambio brusco de iluminación | Detecciones transitorias | Cooldown previene alertas por frames transitorios |

### Métricas de robustez a evaluar en piloto

- Tasa de falsos positivos por hora en condiciones normales vs. adversas
- Tiempo medio de recuperación tras pérdida de conexión
- Estabilidad de tracking (ID switches por hora)

---

## O. Equipo

(Completar con datos del equipo real)

---

## P. Referencias

1. Redmon, J., Divvala, S., Girshick, R., & Farhadi, A. (2016). "You Only Look Once: Unified, Real-Time Object Detection." *CVPR 2016*.
2. Bochkovskiy, A., Wang, C.-Y., & Liao, H.-Y. M. (2020). "YOLOv4: Optimal Speed and Accuracy of Object Detection." *arXiv:2004.10934*.
3. Jocher, G., Chaurasia, A., & Qiu, J. (2023). "Ultralytics YOLOv8." *GitHub: ultralytics/ultralytics*.
4. Deci AI (2023). "YOLO-NAS: A Next-Generation Object Detection Model." *GitHub: Deci-AI/super-gradients* (pesos bajo `LICENSE.YOLONAS.md`).
4b. Roboflow (2025). "RF-DETR: Real-Time Detection Transformer." *GitHub: roboflow/rf-detr* (Apache-2.0 para Nano/Small/Medium).
5. Lin, T.-Y., et al. (2014). "Microsoft COCO: Common Objects in Context." *ECCV 2014*.
6. Zhang, Y., et al. (2022). "ByteTrack: Multi-Object Tracking by Associating Every Detection Box." *ECCV 2022*.
7. Buslaev, A., et al. (2020). "Albumentations: Fast and Flexible Image Augmentations." *Information 2020, 11(2), 125*.
8. Congreso de Colombia (2012). "Ley 1581 de 2012: Ley de Protección de Datos Personales."
9. Superintendencia de Industria y Comercio (SIC). "Guía de Videovigilancia."
10. Meta Platforms (2024). "WhatsApp Business Platform — Pricing." *business.whatsapp.com*.

---

## Anexo: Correspondencia con Observaciones del Jurado

| # | Observación | Sección | Estado |
|---|------------|---------|--------|
| 1 | Arquitectura cloud | D | Documentada |
| 2 | Costos detallados | K | Documentada |
| 3 | YOLO selección y licencia | F | Documentada |
| 4 | Transfer Learning | G | Documentada |
| 5 | Datasets | G | Documentada |
| 6 | Estado del arte | H, P | Documentada |
| 7 | Comparación de modelos | H | Medida: 7 configuraciones en CPU, split de test |
| 8 | Protocolo de evaluación | I | Documentada |
| 9 | Coherencia notificaciones | J | Documentada |
| 10 | Falsos positivos | J | Documentada |
| 11 | Robustez | N | Documentada |
| 12 | Reconocimiento facial futuro | L | Documentada |
| 13 | Protección de datos | M | Documentada |
| 14 | WhatsApp requisitos | J, K | Documentada |
| 15 | Viabilidad económica | K | Documentada |
