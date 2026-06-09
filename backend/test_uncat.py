import asyncio
from app.database import engine
from app.papers.model import Base
from app.papers import crud
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

async def test():
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        uncat = await crud.get_uncategorized_count(db)
        print(f"Uncategorized count: {uncat}")
        tree = await crud.get_folders(db)
        print(f"Folders: {len(tree)} roots")
        print("OK")

asyncio.run(test())
