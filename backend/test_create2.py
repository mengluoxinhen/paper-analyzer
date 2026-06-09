from app.papers import crud
import asyncio
from app.database import engine
from app.papers.model import Base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

async def run():
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        f = await crud.create_folder(db, "测试根目录")
        print(f"OK: id={f.id}, name={f.name}, children={list(f.children)}")
        
        f2 = await crud.create_folder(db, "子目录", parent_id=f.id)
        print(f"OK: child id={f2.id}, name={f2.name}, parent_id={f2.parent_id}")
        
        print("All good!")

asyncio.run(run())
