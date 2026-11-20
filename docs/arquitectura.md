# Arquitectura de SafeRest360

Documento técnico del prototipo tal como está en el código. Para el modelo de IA y su evaluación, ver [`modelo.md`](modelo.md).

## 1. Componentes

| Componente | Carpeta | Tecnología | Qué hace |
|---|---|---|---|
| Frontend | `frontend/` | Next.js 16, React 19, TypeScript, Tailwind | Interfaz del administrador: cámaras, zonas, reglas, alertas, historial y configuración. Detalle en [`frontend/README.md`](../frontend/README.md) |
| Backend API | `backend/` | Python 3.12, FastAPI, SQLAlchemy (asíncrono) | API REST, autenticación, lectura de cámaras en vivo, creación de alertas y envío de notificaciones |
| Motor de visión | `vision-engine/` | Ultralytics YOLOv8n, `supervision` (ByteTrack), OpenCV, Shapely | Detección de personas, seguimiento y reglas por zona. El backend lo importa como librería |
| Base de datos | — | SQLite (desarrollo) o PostgreSQL (Docker Compose) | Restaurantes, usuarios, cámaras, zonas, reglas, alertas y notificaciones |
| Notificaciones | `backend/app/services/` | Telegram Bot API (WhatsApp opcional) | Envía el aviso con la foto al administrador |
| Simulador de cámaras | `tools/` | MediaMTX + FFmpeg | Publica videos como cámaras RTSP para probar sin cámaras reales |

## 2. Flujo de una alerta

```
Cámara IP ──RTSP──▶ CameraWorker (un par de hilos por cámara)
                      │ 1. Hilo de lectura: guarda siempre la imagen más reciente
                      │ 2. Hilo de análisis (≈ 5 imágenes/s por cámara):
                      │      YOLOv8n → personas → ByteTrack → reglas por zona
                      ▼
                    ¿La regla se cumplió el tiempo de confirmación?
                      │ sí
                      ▼
                    PendingAlert (cola) ──▶ persist_alert()
                      │ 3. Guarda la alerta en la base de datos
                      │ 4. Guarda la foto con las personas marcadas en rojo
                      │ 5. Envía el aviso a cada administrador del restaurante
                      ▼
                    Telegram (foto + descripción) ──▶ celular del administrador
```

Detalles del código (`backend/app/services/stream_manager.py`):

1. **Sincronización:** cada 10 segundos (`STREAM_SYNC_SECONDS`) el `StreamManager` lee de la base de datos las cámaras activas con dirección RTSP, sus zonas y sus reglas, y arranca, detiene o actualiza un `CameraWorker` por cámara.
2. **Lectura:** un hilo abre la cámara con OpenCV/FFmpeg (RTSP por TCP) y guarda siempre la imagen más reciente. Si la conexión falla, reintenta con espera creciente de 2 a 30 segundos y muestra el error en la interfaz.
3. **Análisis:** otro hilo procesa la imagen más reciente unas 5 veces por segundo (`STREAM_ANALYSIS_FPS`). Ejecuta el `VisionPipeline` del motor de visión: detección, seguimiento y evaluación de reglas con la hora local del restaurante. También genera la imagen anotada que se ve en vivo en el frontend.
4. **Reglas:** cada regla tiene tipo, tiempo de confirmación, espera entre avisos (`cooldown`) y horario. El evento solo se dispara cuando la condición se mantiene durante el tiempo de confirmación, para no avisar por alguien que solo pasa.
5. **Persistencia:** la alerta y su foto se guardan **antes** de intentar notificar, para que no se pierdan si falla el proveedor de mensajería.
6. **Notificación:** se envía a los usuarios con rol `admin` del mismo restaurante que tengan configurado su chat de Telegram (o su WhatsApp). Si dos administradores comparten el mismo destino, se envía una sola vez. Cada intento queda registrado en la tabla de notificaciones.

### Tipos de regla

| Regla | Zona típica | Se dispara cuando… |
|---|---|---|
| Entrada prohibida (`no_entry`) | Bodega, cuarto técnico | Hay una persona dentro de la zona durante el tiempo de confirmación y dentro del horario |
| Zona sin personal (`zone_abandoned`) | Caja, barra, cocina | La zona queda sin personas más tiempo del permitido (con cuenta regresiva visible) |
| Aforo máximo (`max_occupancy`) | Oficina, área pequeña | Hay más personas que el máximo configurado |

## 3. API REST

Base: `http://localhost:8000/api/v1`. Documentación interactiva generada por FastAPI en `http://localhost:8000/docs`. Todas las rutas, salvo `login`, `refresh` y `/health`, exigen el encabezado `Authorization: Bearer <token>`. Cada usuario solo ve los datos de su propio restaurante.

| Grupo | Método y ruta | Uso |
|---|---|---|
| Salud | `GET /health` (sin prefijo) | Comprobar que el backend está en línea |
| Autenticación | `POST /auth/login` | Iniciar sesión; devuelve token de acceso (30 min) y de renovación (7 días) |
| | `POST /auth/refresh` | Renovar el token de acceso |
| | `GET /auth/me` | Datos del usuario actual |
| Usuarios | `GET /users`, `POST /users` | Listar y crear usuarios del restaurante |
| | `GET /users/{id}`, `PATCH /users/{id}` | Ver y editar un usuario |
| Cámaras | `GET /cameras`, `POST /cameras` | Listar y registrar cámaras |
| | `GET /cameras/{id}`, `PATCH /cameras/{id}`, `DELETE /cameras/{id}` | Ver, editar y eliminar una cámara |
| | `GET /cameras/{id}/live.jpg` | Imagen en vivo con las detecciones dibujadas |
| | `GET /cameras/{id}/live/status` | Estado de la cámara y de cada regla (para las cuentas regresivas) |
| Zonas | `GET /cameras/{id}/zones`, `POST /cameras/{id}/zones` | Listar y crear zonas (polígonos) de una cámara |
| | `GET /zones/{id}`, `PATCH /zones/{id}`, `DELETE /zones/{id}` | Ver, editar y eliminar una zona |
| Reglas | `GET /zones/{id}/rules`, `POST /zones/{id}/rules` | Listar y crear reglas de una zona |
| | `PATCH /rules/{id}`, `DELETE /rules/{id}` | Editar y eliminar una regla |
| Alertas | `GET /alerts` | Listar alertas (filtros: estado, severidad, cámara; máximo 200) |
| | `GET /alerts/{id}`, `PATCH /alerts/{id}`, `DELETE /alerts/{id}` | Ver, cambiar estado (revisada, resuelta, falsa alarma) y eliminar |
| | `GET /alerts/{id}/snapshot` | Foto del momento de la alerta |
| | `POST /alerts/cleanup` | Depurar alertas y fotos antiguas |
| | `GET /dashboard/summary` | Cifras del Dashboard (cámaras activas, alertas de hoy, pendientes y zonas) |
| Notificaciones | `GET /notifications/config` | Canal activo y días de retención |
| | `GET /alerts/{id}/notifications` | Intentos de envío de una alerta |
| Inferencia | `POST /inference/detect` | Detectar personas en una imagen subida |
| | `GET /inference/models`, `POST /inference/models/{id}/promote` | Registro de modelos y cambio del modelo activo |

## 4. Modelo de datos

Tablas en `backend/app/models/`:

```
Restaurant ─┬─< User           (rol, chat de Telegram / WhatsApp)
            └─< Camera ──< Zone ──< Rule
                   │                  │
                   └──────< Alert >───┘ ──< Notification
ModelRegistry  (modelos de visión registrados y cuál está activo)
```

## 5. Configuración

Variables principales del archivo `.env` (ver `.env.example` y `backend/app/config.py`):

| Variable | Valor por defecto | Para qué sirve |
|---|---|---|
| `DATABASE_URL` | SQLite `./saferest360.db` | Base de datos |
| `CORS_ORIGINS` | `http://localhost:3000` | Orígenes del frontend permitidos |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Duración de la sesión |
| `NOTIFICATION_CHANNEL` | `telegram` | `telegram`, `whatsapp` o `disabled` |
| `TELEGRAM_TEST_MODE` | `false` en el código, `true` en Docker Compose | Simula el envío sin llamar a Telegram |
| `STREAM_WORKERS_ENABLED` | `true` | Activa la lectura de cámaras en vivo |
| `STREAM_ANALYSIS_FPS` | 5 | Imágenes analizadas por segundo y por cámara |
| `SNAPSHOT_LOCAL_PATH` | `./snapshots` | Carpeta de las fotos de las alertas |
| `ALERT_RETENTION_DAYS` | 30 | Antigüedad a partir de la cual se pueden depurar alertas y fotos |

## 6. Pendientes de arquitectura

- **Separar la inferencia del backend.** Hoy la captura y la inferencia corren dentro del proceso de la API. El objetivo es un equipo local en el restaurante (`camera-connector/`, aún vacío) que analice el video y envíe solo alertas y fotos a la plataforma.
- **Capacidad con varias cámaras.** Cada cámara se analiza a 5 imágenes/s; con 4 cámaras serían unas 20 imágenes/s, cerca del límite medido para YOLOv8n en CPU (20,1 imágenes/s). Falta medirlo con cámaras reales al mismo tiempo.
- **Imagen Docker del backend.** No instala `vision-engine` ni OpenCV, así que el prototipo completo se ejecuta con la instalación local.
- **Retención automática y cifrado de fotos.** Hoy la depuración de alertas es manual desde el Centro de alertas.
- **Redis** está en Docker Compose, pero el código todavía no lo usa.
