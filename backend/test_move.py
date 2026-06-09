import asyncio
from app.database import engine
from app.papers.model import Base
from app.papers import crud
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

async def run():
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        f = await crud.create_folder(db, "move-test")
        p = await crud.create_paper(db, "test", "t.md", "", "", "content")
        print(f"Paper folder before: {p.folder_id}")

        moved = await crud.move_paper(db, p.id, f.id)
        print(f"Paper folder after: {moved.folder_id}")
        assert moved.folder_id == f.id

        # Move to uncategorized
        moved2 = await crud.move_paper(db, p.id, None)
        print(f"Paper folder uncat: {moved2.folder_id}")
        assert moved2.folder_id is None

        print("Move test PASSED")

asyncio.run(run())
