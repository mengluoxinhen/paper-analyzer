import asyncio
from app.database import engine

from app.papers import crud
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

async def run():
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        folders = await crud.get_folders(db)
        uncat = await crud.get_uncategorized_count(db)
        result = {"folders": folders, "uncategorized_count": uncat}
        print(f"Type: {type(result)}")
        print(f"Keys: {result.keys()}")
        print(f"Uncat: {result['uncategorized_count']}")
        print(f"Folders: {len(result['folders'])}")
        print("OK")

asyncio.run(run())
