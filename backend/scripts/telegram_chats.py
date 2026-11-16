"""List chat IDs after the user starts the bot; no messages are sent."""
import json
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

from app.config import settings


def main():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise SystemExit("Configure TELEGRAM_BOT_TOKEN en .env.")
    try:
        with urlopen(f"https://api.telegram.org/bot{token}/getUpdates", timeout=10) as response:
            data = json.load(response)
        if data.get("ok") is not True:
            raise ValueError()
        chats = {}
        for update in data.get("result", []):
            event = update.get("message") or update.get("my_chat_member") or {}
            chat = event.get("chat", {})
            if "id" in chat:
                chats[chat["id"]] = chat.get("title") or chat.get("first_name") or chat.get("type")
        if not chats:
            print("Sin chats recientes. Abra el bot, envíe /start y vuelva a ejecutar.")
        for chat_id, name in chats.items():
            print(f"{chat_id}: {name}")
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, AttributeError):
        raise SystemExit("No se pudieron consultar los chats. Revise el token y la conexión.") from None


if __name__ == "__main__":
    main()
