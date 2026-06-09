from pydantic import BaseModel


class SettingItem(BaseModel):
    key: str
    value: str | None = None
    model_config = {"from_attributes": True}


class SettingUpdate(BaseModel):
    settings: list[SettingItem]
