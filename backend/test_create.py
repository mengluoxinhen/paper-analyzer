from app.papers import crud
print("crud imported OK")

# Test create_folder function signature
import inspect
sig = inspect.signature(crud.create_folder)
print(f"create_folder params: {list(sig.parameters.keys())}")

# Quick integration test
import asyncio
from app.database import engine
from app.papers.model import Base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

async def run():
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        try:
            f = await crud.create_folder(db, "测试文件夹")
            print(f"Created folder: id={f.id}, name={f.name}, parent_id={f.parent_id}")
            print(f"Children: {f.children}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"ERROR: {e}")

asyncio.run(run())
