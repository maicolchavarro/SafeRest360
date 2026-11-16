"""Manual smoke check. Does not send unless --send is explicitly provided."""
import argparse
import asyncio

from app.config import settings
from app.services.telegram_client import TelegramDeliveryError, send_alert_notification


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat-id", required=True, help="Chat numérico autorizado para la prueba")
    parser.add_argument("--send", action="store_true", help="Enviar realmente a Telegram")
    args = parser.parse_args()
    try:
        result = await send_alert_notification(
            args.chat_id, "prueba", "Prueba de integración del proyecto de IA.", "low",
            token=settings.TELEGRAM_BOT_TOKEN, test_mode=not args.send,
        )
        print("Resultado:", result["status"])
    except TelegramDeliveryError as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    asyncio.run(main())
