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

**Variantes evaluadas:**

| Modelo | Autor | Licencia | Parámetros | Implicación SaaS |
|--------|-------|----------|------------|-------------------|
| YOLOv8n | Ultralytics | AGPL-3.0 | 3.2M | Requiere licencia Enterprise para SaaS comercial |
| YOLOv8s | Ultralytics | AGPL-3.0 | 11.2M | Requiere licencia Enterprise para SaaS comercial |
| YOLOv8m | Ultralytics | AGPL-3.0 | 25.9M | Requiere licencia Enterprise para SaaS comercial |
| YOLO-NAS-S | Deci AI | Apache-2.0 | ~12M | Libre para uso comercial sin restricciones |

### Análisis de licencias

La licencia **AGPL-3.0** de Ultralytics exige que cualquier software que use los modelos YOLOv8 y se distribuya como servicio (SaaS) debe publicar su código fuente completo, o adquirir una licencia Enterprise (~US$1,500/año para startups).

**YOLO-NAS-S** (Deci AI) utiliza licencia **Apache-2.0**, que permite uso comercial sin restricciones de publicación de código. Esta es la opción recomendada para SafeRest360 como producto SaaS.

**Estrategia**: Usar YOLOv8 durante desarrollo y validación académica (cobertura AGPL es aceptable para investigación). Para producción comercial, migrar a YOLO-NAS-S o adquirir licencia Enterprise de Ultralytics.

---

## G. Dataset y Entrenamiento por Transfer Learning

> **[Observaciones del jurado #4 y #5: Transfer Learning y datasets]**

### Dataset: COCO 2017 — Extracción de clase persona

Se utiliza el dataset **COCO 2017** (Common Objects in Context, Microsoft), que contiene 118K imágenes de entrenamiento y 5K de validación con 80 categorías anotadas.

**Proceso de extracción:**
1. Filtrar anotaciones con `category_id == 1` (persona) y `iscrowd == 0`
2. Convertir bounding boxes de formato COCO `[x, y, w, h]` (píxeles) a formato YOLO `[class x_center y_center width height]` (normalizado 0-1)
3. Copiar solo las imágenes que contienen al menos una persona

**Resultado:** ~64.000 imágenes con ~262.000 anotaciones de personas.

### Augmentación de datos

Pipeline de aumentación con Albumentations (MIT license):
- HorizontalFlip (p=0.5)
- RandomBrightnessContrast (límite ±0.2)
- GaussNoise (var_limit 10-50)
- MotionBlur (kernel 3-7)
- GaussianBlur (kernel 3-7)
- RandomScale (±10%)

Estas aumentaciones simulan condiciones reales de videovigilancia: cambios de iluminación, ruido de cámara, movimiento.

### Protocolo de Transfer Learning

1. **Preentrenamiento**: Todos los modelos inician con pesos preentrenados en COCO completo (80 clases).
2. **Fine-tuning**: Se reentrena sobre el subconjunto de personas con `single_cls=True` (una sola clase: persona).
3. **Configuración**: epochs=100, imgsz=640, batch=16, optimizer=AdamW, lr0=0.001, early stopping patience=20.
4. **Reproducibilidad**: seed=42, registros en MLflow.

El Transfer Learning permite que los modelos mantengan las features de bajo nivel aprendidas en COCO (bordes, texturas, formas) y especialicen las capas superiores en detección de personas en contexto de restaurantes.

---

## H. Comparación de Modelos y Resultados

> **[Observaciones del jurado #6 y #7: Estado del arte y comparación]**

### Estado del arte en detección de personas

| Referencia | Método | mAP (COCO) | Notas |
|-----------|--------|------------|-------|
| Redmon et al. (2016) | YOLOv1 | 63.4 | Primera propuesta single-shot |
| Bochkovskiy et al. (2020) | YOLOv4 | 65.7 | CSPDarknet backbone |
| Jocher et al. (2023) | YOLOv8 | 53.9 (mAP50-95) | Anchor-free, estado del arte actual |
| Deci AI (2023) | YOLO-NAS | 52.2 (mAP50-95) | Neural Architecture Search, Apache-2.0 |

### Tabla comparativa (placeholder — completar con resultados reales de Colab)

| Métrica | YOLOv8n | YOLOv8s | YOLOv8m | YOLO-NAS-S |
|---------|---------|---------|---------|------------|
| mAP@50 | Pendiente | Pendiente | Pendiente | Pendiente |
| mAP@50-95 | Pendiente | Pendiente | Pendiente | Pendiente |
| Precision | Pendiente | Pendiente | Pendiente | Pendiente |
| Recall | Pendiente | Pendiente | Pendiente | Pendiente |
| F1 | Pendiente | Pendiente | Pendiente | Pendiente |
| Latencia (ms) | Pendiente | Pendiente | Pendiente | Pendiente |
| FPS (T4 GPU) | Pendiente | Pendiente | Pendiente | Pendiente |
| Tamaño modelo | 6.2 MB | 22.5 MB | 52.0 MB | ~30 MB |
| Licencia | AGPL-3.0 | AGPL-3.0 | AGPL-3.0 | Apache-2.0 |

> **Nota**: Los valores "Pendiente" se completan ejecutando el notebook `colab/SafeRest360_Training.ipynb` en Google Colab con GPU. No se inventan resultados de entrenamiento.

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

- **Benchmark**: Warmup 50 inferencias + medición de 200 inferencias
- **Métricas**: Latencia media, P95, FPS, uso de memoria GPU
- **Hardware de referencia**: NVIDIA T4 (16 GB VRAM, cloud)

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
4. Deci AI (2023). "YOLO-NAS: A Next-Generation Object Detection Model." *GitHub: Deci-AI/super-gradients*.
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
| 7 | Comparación de modelos | H | Pendiente resultados Colab |
| 8 | Protocolo de evaluación | I | Documentada |
| 9 | Coherencia notificaciones | J | Documentada |
| 10 | Falsos positivos | J | Documentada |
| 11 | Robustez | N | Documentada |
| 12 | Reconocimiento facial futuro | L | Documentada |
| 13 | Protección de datos | M | Documentada |
| 14 | WhatsApp requisitos | J, K | Documentada |
| 15 | Viabilidad económica | K | Documentada |
