import uuid
from sqlalchemy import Column, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Setting(Base):
    __tablename__ = "settings"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
