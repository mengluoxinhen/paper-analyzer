import asyncio
import traceback
from app.database import engine
from app.papers.model import Base
from app.papers import crud
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

async def test():
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    print("Tables OK")

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        # Test folders
        folders = await crud.get_folders(db)
        print(f"Folders: {folders}")

        # Test tags
        tags = await crud.get_tags(db)
        print(f"Tags: {tags}")

        # Test papers
        papers, total = await crud.get_papers(db, page=1, page_size=2)
        print(f"Papers count: {total}")

    print("All tests passed!")

asyncio.run(test())
