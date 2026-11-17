# SafeRest360 · Frontend

Aplicación web con la que el administrador del restaurante registra cámaras, dibuja zonas, configura reglas y revisa las alertas que genera el motor de visión.

## Tecnologías

| Componente | Versión |
|---|---|
| Next.js (App Router, Turbopack) | 16.4 |
| React | 19.3 |
| TypeScript | 5 |
| Tailwind CSS | 4.3 |
| Axios (cliente de la API) | 1.x |
| Recharts (gráficos) | 3.x |
| lucide-react (iconos) | 1.x |

## Cómo ejecutar

Requiere Node.js 20 o superior y el backend corriendo en `http://localhost:8000` (ver el README principal).

```bash
npm install
npm run dev
```

Abrir la dirección que muestre la terminal (normalmente http://localhost:3000). Usuario de demostración: `admin@saferest360.com` / `admin123`.

Otros comandos: `npm run build` (compilación de producción), `npm run start` (servir la compilación) y `npm run lint` (revisión de estilo).

### Variable de entorno

| Variable | Valor por defecto | Uso |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Dirección base de la API REST del backend |

Si el frontend se abre en otro puerto (por ejemplo 3001), ese origen debe estar en `CORS_ORIGINS` del archivo `.env` del backend.

## Pantallas

| Ruta | Pantalla | Qué permite hacer |
|---|---|---|
| `/login` | Ingreso | Iniciar sesión con correo y contraseña. |
| `/dashboard` | Dashboard | Ver cámaras activas, alertas de hoy, alertas pendientes y zonas configuradas; gráfico de alertas reales por hora del día y las últimas alertas sin revisar. |
| `/cameras` | Cámaras | Registrar, editar y eliminar cámaras (nombre, ubicación, URL RTSP, tipo de fuente y FPS). |
| `/cameras/[id]` | Vista de cámara | Ver la imagen en vivo con las detecciones, dibujar zonas como polígonos sobre la imagen, editarlas o eliminarlas, y configurar las reglas de cada zona. Muestra el estado de cada regla con cuenta regresiva. |
| `/alerts` | Centro de alertas | Filtrar alertas por estado, ver la foto del momento, marcarlas como revisadas, resueltas o falsa alarma, eliminarlas y depurar alertas y fotos antiguas. |
| `/history` | Historial | Tabla de eventos con fecha, tipo, descripción, severidad y estado. |
| `/settings` | Configuración | Datos del usuario, estado del canal de notificaciones (Telegram), días de retención de fotos y aspectos de privacidad. |

La ruta `/` redirige al Dashboard. Todas las pantallas, salvo el ingreso, exigen sesión iniciada.

### Zonas y reglas

| Tipo de zona | Uso típico |
|---|---|
| Restringida | Bodega o caja fuera de horario: nadie debe entrar. |
| Monitoreada | Área de trabajo que no debe quedar sola. |
| Presencia requerida | Área donde siempre debe haber alguien. |

Cada zona puede tener reglas de tipo **Entrada prohibida**, **Zona sin personal** o **Aforo máximo**, con severidad (baja, media, alta o crítica), tiempo de confirmación, espera entre avisos y horario.

## Estructura del código

```
src/
├── app/                    Pantallas (una carpeta por ruta)
│   ├── layout.tsx          Estructura general y proveedor de sesión
│   ├── login/  dashboard/  cameras/  cameras/[id]/  alerts/  history/  settings/
├── components/
│   ├── layout/             Menú lateral, barra superior y protección de rutas (AppShell)
│   ├── zones/              Lienzo para ver la cámara y dibujar zonas
│   └── rules/              Editor de reglas por zona
├── context/
│   └── auth-context.tsx    Inicio y cierre de sesión; guarda los tokens en localStorage
└── lib/
    ├── api.ts              Cliente Axios: auth, cameras, zones, rules, alerts, dashboard, notifications
    ├── types.ts            Tipos de datos compartidos con la API
    ├── zone-state.ts       Estado en vivo de cada zona (colores y cuentas regresivas)
    └── utils.ts            Formato de fechas y colores por severidad y estado
```

## Cómo se comunica con el backend

- **Sesión:** al ingresar se guardan el token de acceso y el de renovación en `localStorage`. Cada petición envía `Authorization: Bearer <token>`. Si la API responde 401 (por ejemplo, porque el token expiró a los 30 minutos), se borran los tokens y se vuelve a `/login`.
- **Vista en vivo:** la pantalla de una cámara pide la imagen procesada (`/cameras/{id}/live.jpg`) cada 300 ms, o cada 2 s si falla, y el estado de las reglas (`/cameras/{id}/live/status`) cada segundo.
- **Fotos de alertas:** se descargan bajo demanda desde `/alerts/{id}/snapshot`.

## Limitaciones conocidas

- En Configuración, el nombre del restaurante, la zona horaria, el plan y el texto de la política de datos son valores fijos de la interfaz; todavía no se leen de la API.
- La sesión no se renueva sola: al expirar el token hay que volver a ingresar.
- La vista en vivo usa consultas periódicas (polling), no WebSockets.
