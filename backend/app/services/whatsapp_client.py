"""WhatsApp Business Cloud API client.

In test mode (no credentials configured), messages are logged to console.
In production, messages are sent via Meta's WhatsApp Business API.
"""

import logging
from app.config import settings

logger = logging.getLogger("saferest360.whatsapp")


async def send_alert_notification(phone: str, alert_type: str, description: str, severity: str):
    """Send a WhatsApp alert notification to the given phone number."""
    message = (
        f"*SafeRest360 — Alerta {severity.upper()}*\n\n"
        f"Tipo: {alert_type}\n"
        f"{description}\n\n"
        f"_Este es un aviso para revisión. La decisión final la toma una persona._"
    )

    if settings.WHATSAPP_TEST_MODE:
        logger.info(f"[WHATSAPP TEST] To: {phone}\n{message}")
        return {"status": "test", "message": "Logged to console (test mode)"}

    import httpx
    url = f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return {
            "status": "sent",
            "message_id": data.get("messages", [{}])[0].get("id"),
        }
