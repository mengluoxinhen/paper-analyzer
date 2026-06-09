import asyncio
from app.database import engine
from app.papers.model import Base
from app.papers import crud
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

async def test():
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        # Depth test
        f1 = await crud.create_folder(db, "根-A")
        f2 = await crud.create_folder(db, "子-B", parent_id=f1.id)
        f3 = await crud.create_folder(db, "孙-C", parent_id=f2.id)
        try:
            await crud.create_folder(db, "曾孙-应拒绝", parent_id=f3.id)
            print("ERROR: level 4 should be rejected")
        except ValueError as e:
            print(f"OK: level 4 rejected: {e}")

        # Tree structure
        tree = await crud.get_folders(db)
        roots = len(tree)
        print(f"Tree roots: {roots}")

        # Delete cascade test
        await crud.delete_folder(db, f1.id)
        tree = await crud.get_folders(db)
        print(f"After delete: {len(tree)} roots")

        print("All OK!")

asyncio.run(test())
