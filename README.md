# SafeRest360

Plataforma SaaS de videovigilancia inteligente para restaurantes.

Aprovecha las cámaras de seguridad existentes para detectar situaciones relevantes mediante inteligencia artificial y notificar al administrador por WhatsApp.

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

### Entrenamiento completo (Google Colab)
Abrir `colab/SafeRest360_Training.ipynb` en Google Colab con GPU habilitada.

## Tecnologías

| Componente | Tecnología |
|------------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| Base de datos | PostgreSQL (prod) / SQLite (dev) |
| Visión artificial | YOLO (Ultralytics + YOLO-NAS), PyTorch, OpenCV |
| Seguimiento | ByteTrack (via supervision) |
| Experimentación | MLflow |
| Notificaciones | WhatsApp Business Platform |
| Infraestructura | Docker Compose |

## Licencia

Proyecto académico — Universidad de Boyacá, Ingeniería de Sistemas.
