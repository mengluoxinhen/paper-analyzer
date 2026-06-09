from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import DBSession
from app.settings import schemas, crud

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=list[schemas.SettingItem])
async def list_settings(db: AsyncSession = DBSession):
    return await crud.get_all(db)


@router.put("", response_model=list[schemas.SettingItem])
async def update_settings(body: schemas.SettingUpdate, db: AsyncSession = DBSession):
    items = [s.model_dump() for s in body.settings]
    return await crud.upsert_all(db, items)
