from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.settings.model import Setting


async def get_all(db: AsyncSession) -> list[Setting]:
    result = await db.execute(select(Setting))
    return list(result.scalars().all())


async def upsert_all(db: AsyncSession, items: list[dict]) -> list[Setting]:
    results = []
    for item in items:
        result = await db.execute(select(Setting).where(Setting.key == item["key"]))
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = item["value"]
            results.append(existing)
        else:
            new_item = Setting(key=item["key"], value=item["value"])
            db.add(new_item)
            results.append(new_item)
    await db.commit()
    return results
