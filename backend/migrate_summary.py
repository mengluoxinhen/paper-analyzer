import asyncio
from app.database import engine
from sqlalchemy import text

async def run():
    async with engine.begin() as c:
        # Rename background -> problem
        try:
            await c.execute(text("ALTER TABLE summaries CHANGE background problem TEXT"))
            print("background -> problem")
        except Exception as e:
            print(f"Skip background: {e}")
        # Rename results -> conditions
        try:
            await c.execute(text("ALTER TABLE summaries CHANGE results conditions TEXT"))
            print("results -> conditions")
        except Exception as e:
            print(f"Skip results: {e}")
        # Drop old methods column (no longer used)
        try:
            await c.execute(text("ALTER TABLE summaries DROP COLUMN methods"))
            print("dropped methods")
        except Exception as e:
            print(f"Skip drop methods: {e}")
        print("Migration done")

asyncio.run(run())
