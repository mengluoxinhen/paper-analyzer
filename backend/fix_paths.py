import asyncio
from app.database import async_session
from app.papers.model import Paper
from sqlalchemy import select

async def fix():
    async with async_session() as db:
        result = await db.execute(select(Paper))
        papers = result.scalars().all()
        for p in papers:
            print(f"Before: {p.id} -> {p.md_path}")
            if p.md_path and p.md_path.startswith("./uploads"):
                p.md_path = "C:/myweb/backend/uploads/papers/" + p.md_path.rsplit("\\", 1)[-1]
                print(f"  After: {p.id} -> {p.md_path}")
        await db.commit()
        print("Done")

asyncio.run(fix())
