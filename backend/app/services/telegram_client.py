"""Small Telegram Bot API client; no SDK, webhook or public server required.

Only outbound text is sent. An accepted message is not a read receipt.
Never retry an ambiguous timeout automatically (it may duplicate an alert).
"""
import asyncio
import json
import logging
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("saferest360.telegram")


class TelegramDeliveryError(Exception):
    def __init__(self, message: str, status: str = "failed"):
        super().__init__(message)
        self.status = status


def normalize_chat_id(chat_id: str) -> str:
    value = str(chat_id).strip()
    if not re.fullmatch(r"-?[1-9][0-9]{0,19}", value):
        raise TelegramDeliveryError("El chat_id debe ser un identificador numérico de Telegram.")
    return value


def _post_message(token: str, payload: dict, timeout: float) -> dict:
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except HTTPError as exc:
        # Do not expose the exception/URL: Telegram places the secret token in it.
        status = "unknown" if exc.code >= 500 else "failed"
        raise TelegramDeliveryError(f"Telegram rechazó el envío (HTTP {exc.code}).", status) from None
    except (URLError, TimeoutError, OSError):
        raise TelegramDeliveryError(
            "No se pudo confirmar el envío a Telegram; revisar el chat antes de reintentar.",
            "unknown",
        ) from None
    except (ValueError, UnicodeError):
        raise TelegramDeliveryError("Respuesta de Telegram no reconocida.", "unknown") from None

    if not isinstance(data, dict):
        raise TelegramDeliveryError("Respuesta de Telegram no reconocida.", "unknown")
    if data.get("ok") is not True:
        raise TelegramDeliveryError("Telegram no aceptó el mensaje.")
    result = data.get("result")
    message_id = result.get("message_id") if isinstance(result, dict) else None
    if type(message_id) is not int or message_id <= 0:
        raise TelegramDeliveryError("Telegram no devolvió un identificador válido.", "unknown")
    # Telegram IDs are unique within a chat, not globally.
    return {"status": "sent", "message_id": f"{payload['chat_id']}:{message_id}"}


async def send_alert_notification(
    chat_id: str, alert_type: str, description: str, severity: str, *,
    token: str | None = None, test_mode: bool = True, timeout: float = 10.0,
) -> dict:
    recipient = normalize_chat_id(chat_id)
    message = (
        f"SafeRest360 — Alerta {severity.upper()}\n\n"
        f"Tipo: {alert_type}\n{description}\n\n"
        "Aviso para revisión. La decisión final la toma una persona."
    )
    if len(message) > 4000:
        message = message[:3850] + "\n[Detalle abreviado; consulte SafeRest360.]"
    if test_mode:
        logger.info("[TELEGRAM TEST] Envío simulado; no se contactó a Telegram.")
        return {"status": "test", "message_id": None}
    if not token or not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", token):
        raise TelegramDeliveryError("Configure TELEGRAM_BOT_TOKEN en el backend.")
    if not 0 < timeout <= 60:
        raise TelegramDeliveryError("El timeout debe estar entre 0 y 60 segundos.")
    payload = {
        "chat_id": recipient,
        "text": message,
        "link_preview_options": {"is_disabled": True},
    }
    # urllib is blocking; keep camera processing / the FastAPI loop responsive.
    return await asyncio.to_thread(_post_message, token, payload, timeout)
