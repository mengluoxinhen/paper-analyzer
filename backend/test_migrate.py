import asyncio
import traceback
from app.database import engine
from app.papers.model import Base

async def test():
    try:
        async with engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        print("Tables OK")
    except Exception as e:
        traceback.print_exc()
        print(f"ERROR: {e}")

asyncio.run(test())
