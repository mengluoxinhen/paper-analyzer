import asyncio
from sqlalchemy import text
from app.database import async_session

async def check():
    async with async_session() as db:
        r = await db.execute(text("SELECT id, name, parent_id, knowledge_base_id FROM folders"))
        rows = r.fetchall()
        print(f"Folders: {len(rows)}")
        for row in rows:
            print(f"  id={row[0][:8]}... name={row[1]} parent={row[2]} kb={row[3][:8] if row[3] else 'None'}...")

asyncio.run(check())
