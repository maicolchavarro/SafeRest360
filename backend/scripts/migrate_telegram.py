"""Run once before starting an EXISTING database: python -m scripts.migrate_telegram."""
import asyncio

from sqlalchemy import inspect, text
from app.database import engine


async def main():
    async with engine.begin() as connection:
        def needs_column(sync_connection):
            inspector = inspect(sync_connection)
            return inspector.has_table("users") and "telegram_chat_id" not in {
                c["name"] for c in inspector.get_columns("users")
            }
        if await connection.run_sync(needs_column):
            await connection.execute(text("ALTER TABLE users ADD COLUMN telegram_chat_id VARCHAR(32)"))
            print("Columna telegram_chat_id agregada.")
        else:
            print("No hay cambios pendientes; las bases nuevas se crean al iniciar la API.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
