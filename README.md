# SafeRest360

Plataforma SaaS de videovigilancia inteligente para restaurantes.

Aprovecha las cámaras de seguridad existentes para detectar situaciones relevantes mediante inteligencia artificial y notificar al administrador por Telegram (WhatsApp queda como cliente legado).

## Arquitectura

```
┌────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Frontend   │────▶│  Backend API │────▶│  Vision Engine   │
│  (Next.js)  │◀────│  (FastAPI)   │◀────│  (YOLO + Rules)  │
└────────────┘     └──────┬───────┘     └──────────────────┘
                          │
                   ┌──────▼───────┐     ┌──────────────────┐
                   │  PostgreSQL  │     │ Camera Connector  │
                   │  + Redis     │     │  (RTSP → Cloud)   │
                   └──────────────┘     └──────────────────┘
```

## Estructura del proyecto

- `vision-engine/` — Motor de visión artificial (YOLO, entrenamiento, inferencia, reglas)
- `backend/` — API REST (FastAPI, autenticación, CRUD, alertas)
- `frontend/` — Aplicación web (Next.js, TypeScript, Tailwind)
- `camera-connector/` — Conector local para cámaras IP (RTSP)
- `infrastructure/` — Docker, nginx, scripts de despliegue
- `docs/` — Documentación técnica y Brief corregido
- `colab/` — Notebooks de Google Colab para entrenamiento con GPU

## Inicio rápido

### Backend
```bash
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env
python -m app.main
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Vision Engine (prueba CPU)
```bash
cd vision-engine
pip install -r requirements.txt
pytest tests/ -v
```

### Entrenamiento y evaluación local (CPU)
```bash
cd vision-engine
python -m venv .venv && .venv\Scripts\activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install ultralytics albumentations "supervision<0.31" shapely lapx rfdetr pycocotools pytest
# descargar COCO val2017 + anotaciones en vision-engine/data/
python train_local.py prepare
python train_local.py train --variants yolov8n --epochs 15 --imgsz 416 --no-offline-aug
python train_local.py evaluate
```
Resultados en `vision-engine/experiments/eval_results.md` (resumen en la sección H del Brief).

### Cámaras en vivo (RTSP)
El backend lee cada cámara activa con URL `rtsp://`/`rtsps://`:
- analiza ~5 cuadros/s con YOLOv8n → ByteTrack → reglas de zona;
- guarda una alerta con foto cuando se cumple una regla;
- muestra la vista en vivo en la página de la cámara.

Los cuadros en vivo solo viven en memoria. Para probar sin cámaras reales, ver [`tools/README.md`](tools/README.md) (MediaMTX + videos con licencia libre).

### Entrenamiento con GPU (Google Colab)
Abrir `colab/SafeRest360_Training.ipynb` en Google Colab con GPU habilitada.

## Tecnologías

| Componente | Tecnología |
|------------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| Base de datos | PostgreSQL (prod) / SQLite (dev) |
| Visión artificial | YOLOv8n preentrenado (Ultralytics, AGPL-3.0); RF-DETR (Apache-2.0) evaluado para producción; PyTorch, OpenCV |
| Seguimiento | ByteTrack (via supervision) |
| Experimentación | Registros JSON por experimento + evaluación COCO (pycocotools) |
| Notificaciones | Telegram Bot API (predeterminado, modo simulado por defecto) |
| Infraestructura | Docker Compose |

## Licencia

Proyecto académico — Universidad de Boyacá, Ingeniería de Sistemas.

## Alertas por Telegram

Configuración del bot, migración de la base existente y prueba controlada:
[Guía de integración](docs/telegram.md).
