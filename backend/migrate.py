import asyncio
from app.database import engine
from sqlalchemy import text

async def run():
    async with engine.begin() as c:
        # Add parent_id column
        await c.execute(text("ALTER TABLE folders ADD COLUMN parent_id INT NULL"))
        print("1. parent_id column added")

        # Drop old unique constraint on name (MySQL auto-indexes unique columns)
        try:
            await c.execute(text("ALTER TABLE folders DROP INDEX name"))
            print("2. old unique constraint dropped")
        except Exception:
            print("2. old unique constraint not found (ok)")

        # Add composite unique
        try:
            await c.execute(text("ALTER TABLE folders ADD UNIQUE KEY uq_folder_name_parent (name, parent_id)"))
            print("3. composite unique added")
        except Exception as e:
            print(f"3. composite unique: {e}")

        print("Migration done!")

asyncio.run(run())
