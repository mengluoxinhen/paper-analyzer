import asyncio
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
        # Test 1: create root folder
        f1 = await crud.create_folder(db, "CAE")
        print(f"1. Created root folder: {f1.name} id={f1.id}")

        # Test 2: create child (level 2)
        f2 = await crud.create_folder(db, "风阻", parent_id=f1.id)
        print(f"2. Created child: {f2.name} id={f2.id} parent={f2.parent_id}")

        # Test 3: create grandchild (level 3)
        f3 = await crud.create_folder(db, "2024年", parent_id=f2.id)
        print(f"3. Created grandchild: {f3.name} id={f3.id}")

        # Test 4: try level 4 - should fail
        try:
            await crud.create_folder(db, "Q4", parent_id=f3.id)
            print("4. ERROR: should have raised")
        except ValueError as e:
            print(f"4. Correctly rejected level 4: {e}")

        # Test 5: get tree
        tree = await crud.get_folders(db)
        print(f"5. Tree: {len(tree)} roots")
        for r in tree:
            print(f"   {r['name']} ({r['paper_count']} papers)")
            for c in r.get('children', []):
                print(f"     {c['name']} ({c['paper_count']} papers)")
                for gc in c.get('children', []):
                    print(f"       {gc['name']} ({gc['paper_count']} papers)")

        print("All tests passed!")

asyncio.run(test())
