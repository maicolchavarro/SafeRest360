# Alertas por Telegram — SafeRest360

Esta rama implementa Telegram como canal predeterminado. La API de bots no tiene
cargo por mensaje para el volumen habitual de este proyecto académico; sí tiene
límites de frecuencia. El alojamiento del backend y el procesamiento de video
siguen siendo costos separados. No se usan mensajes masivos de pago ni intermediarios.

Fuentes: https://core.telegram.org/bots y https://core.telegram.org/bots/faq

## 1. Crear el bot

1. Abra https://t.me/BotFather en Telegram y use /newbot.
2. Asigne nombre y usuario al bot. Guarde el token en el .env del backend,
   nunca en GitHub, el frontend, capturas de pantalla ni mensajes compartidos.
3. Abra el enlace de su bot y pulse Iniciar o envíe /start.
   El bot no puede iniciar una conversación privada con alguien que no lo ha iniciado.
4. Para una demo, use un chat privado del administrador. Si usa un grupo,
   agregue el bot y compruebe que todos autorizan recibir esos avisos.

No necesita webhook, dominio público ni túnel para el envío de alertas.
El backend solo requiere salida HTTPS hacia api.telegram.org.

## 2. Configurar el backend

Desde la raíz del repositorio, copie .env.example a .env si todavía no existe.
No sobrescriba un .env existente.

    NOTIFICATION_CHANNEL=telegram
    TELEGRAM_TEST_MODE=true
    TELEGRAM_BOT_TOKEN=TOKEN_ENTREGADO_POR_BOTFATHER
    DATABASE_URL=sqlite+aiosqlite:///./saferest360.db

El backend carga el .env de la raíz y después backend/.env, si existe.
Las variables del entorno prevalecen. No se selecciona WhatsApp como respaldo automático.
Para desactivar envíos: NOTIFICATION_CHANNEL=disabled.

Instale las dependencias según el README. Si mantiene una base existente, haga
una copia de seguridad y, con el backend detenido, ejecute desde backend:

    python -m scripts.migrate_telegram

La migración agrega una columna opcional a users. Es idempotente y funciona con
SQLite y PostgreSQL. No elimina datos. Una base nueva crea la columna al arrancar.
Ejecute la migración una sola vez por base y sin otros procesos migrando simultáneamente.

    python -m scripts.telegram_chats

Este comando consulta getUpdates y muestra los chat_id recientes. Ejecútelo después
de enviar /start. No configura un webhook ni confirma/borra actualizaciones mediante offset.
Si ya hay otro programa consumiendo las actualizaciones o un webhook, use un bot
exclusivo para la demo; no elimine la configuración de otro sistema.

## 3. Asociar el chat con el administrador

Inicie el backend y abra http://localhost:8000/docs.
Inicie sesión mediante POST /api/v1/auth/login y copie el access_token en Authorize.
Consulte GET /api/v1/auth/me para obtener su id.

PATCH /api/v1/users/{id}, autenticado como administrador:

    {"telegram_chat_id": "123456789"}

Use el identificador devuelto por el comando, no el número telefónico ni @username.
Los grupos pueden tener identificadores negativos. Para dejar de recibir mensajes:

    {"telegram_chat_id": null}

Solo se notifican administradores activos del mismo restaurante que la cámara.
Si varios administradores del restaurante comparten chat, se envía una sola copia por alerta.
El administrador debe registrar únicamente chats autorizados de su restaurante.

Consulte GET /api/v1/notifications/config para comprobar canal, modo de prueba y
configuración del destinatario. El endpoint no expone el token.
La pantalla de Configuración consulta el canal y modo reales del backend.
El estado indica configuración, no garantiza que Telegram haya recibido un aviso.

## 4. Prueba controlada

Desde backend:

    python -m scripts.test_telegram --chat-id 123456789

Simula sin enviar. Para enviar UN mensaje de prueba al chat autorizado:

    python -m scripts.test_telegram --chat-id 123456789 --send

El indicador --send autoriza el envío real de ese comando, aunque TELEGRAM_TEST_MODE
siga en true. No cambia la configuración de las cámaras.

Cuando esa prueba funcione, cambie TELEGRAM_TEST_MODE=false y reinicie el backend.
Active una regla de una cámara. Cuando la regla genere una alerta, se enviará el aviso.
Se conserva el cooldown_seconds de cada regla para evitar mensajes en cada cuadro.
Cada regla/cámara puede generar avisos independientes; ajuste sus tiempos si se
acumulan mensajes. No hay reintentos automáticos ni gasto por WhatsApp en modo Telegram.

## 5. Verificación y estados

GET /api/v1/alerts/{alert_id}/notifications devuelve el historial de la alerta,
limitado al restaurante del usuario.

- pending: intento registrado; puede quedar así si el proceso se interrumpe.
- test: envío simulado, sin fecha real de envío.
- sent: Telegram aceptó y creó el mensaje; no confirma lectura del administrador.
- failed: rechazo explícito o configuración inválida.
- unknown: timeout, fallo de red o respuesta ambigua; revise el chat antes de repetir.

La alerta y su snapshot se guardan antes de contactar al proveedor.
Los avisos incluyen la captura de la alerta, con las detecciones resaltadas.
Solo registre chats autorizados para recibir estas imágenes. Ante un rechazo de
formato o tamaño de la foto se intenta texto; ante timeout, falta de permisos
o límites de frecuencia no se envía un segundo mensaje.
Los errores guardados no incluyen el token ni la URL con credenciales.

Si Telegram responde 403, compruebe si el bot fue bloqueado o perdió acceso al chat.
Si responde 429, reduzca frecuencia y espere antes de una prueba manual.
Esta versión no implementa cola persistente de reintentos, recuperación de pending,
confirmaciones de lectura ni garantía de entrega exactamente una vez. Para un
despliegue real, esas capacidades requieren un worker y una cola transaccional.

## 6. Docker

Use desde la raíz:

    docker compose --env-file .env -f infrastructure/docker-compose.yml up -d --build

Para una base existente, ejecute la migración en el contenedor antes de iniciar
el proceso de la API. El compose transmite NOTIFICATION_CHANNEL,
TELEGRAM_TEST_MODE y TELEGRAM_BOT_TOKEN. La integración de cámaras del Dockerfile
existente tiene requisitos propios del motor de visión y no se reestructura aquí.

## 7. Pruebas y rama

Pruebas aisladas del cliente, sin servicios externos ni dependencias de FastAPI:

    cd backend
    python -m unittest discover -s tests -p test_telegram_client.py -v

Con las dependencias del backend y OpenCV disponibles:

    python -m pytest tests -q -k "not worker_reads_stream_detects_people_and_fires_rule"

Hay pruebas de transporte simulado, validación de destinatarios, errores, límites del
mensaje, persistencia ante fallos, permisos y aislamiento entre restaurantes.
El workflow de GitHub ejecutará el backend al subir feat/telegram-alerts o abrir PR.
No incluye la prueba que necesita video/modelo de visión.

Trabaje en feat/telegram-alerts y abra un PR hacia master. Revise el diff, espere
los checks y complete la prueba real con el bot antes de fusionar.
La integración no ha sido validada con un bot real durante su preparación.

## 8. Depuración manual del historial

Los administradores pueden eliminar una alerta y su captura desde el Centro de
Alertas, o depurar registros anteriores a un número entero de 1 a 365 días.
El valor predeterminado del backend es ALERT_RETENTION_DAYS=30.
La depuración es manual, no un borrado automático programado.

Las operaciones están limitadas al restaurante autenticado y las capturas deben
estar dentro de su directorio de almacenamiento. Si falla el borrado del archivo,
se conserva la alerta para poder reintentar. La respuesta informa cuántas alertas
se omitieron. El disco y la base de datos no comparten una transacción: un fallo
de base de datos posterior a borrar una imagen exige reconciliación manual.

Endpoints de administrador:
- DELETE /api/v1/alerts/{alert_id}
- POST /api/v1/alerts/cleanup?older_than_days=30
