from datetime import datetime
import uuid

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, func, Table, UniqueConstraint
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import DeclarativeBase


def _new_uuid() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


paper_tags = Table(
    "paper_tags",
    Base.metadata,
    Column("paper_id", String(32), primary_key=True),
    Column("tag_id", String(32), primary_key=True),
)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(String(32), primary_key=True, default=_new_uuid)
    name = Column(String(200), nullable=False)
    description = Column(String(1000), default="")
    user_id = Column(String(32), nullable=True, default=None, index=True)
    is_shared = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class Folder(Base):
    __tablename__ = "folders"
    __table_args__ = (UniqueConstraint("name", "parent_id", "knowledge_base_id", name="uq_folder_name_parent_kb"),)

    id = Column(String(32), primary_key=True, default=_new_uuid)
    name = Column(String(200), nullable=False)
    parent_id = Column(String(32), nullable=True, default=None)
    knowledge_base_id = Column(String(32), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("name", "knowledge_base_id", name="uq_tag_name_kb"),)

    id = Column(String(32), primary_key=True, default=_new_uuid)
    name = Column(String(100), nullable=False)
    knowledge_base_id = Column(String(32), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())


class Paper(Base):
    __tablename__ = "papers"

    id = Column(String(32), primary_key=True, default=_new_uuid)
    title = Column(String(500), default="")
    filename = Column(String(500), nullable=False)
    pdf_path = Column(String(1000), default="")
    md_content = Column(LONGTEXT, default="")
    status = Column(String(50), default="uploaded")
    mineru_batch_id = Column(String(200), default="")
    folder_id = Column(String(32), nullable=True, default=None)
    knowledge_base_id = Column(String(32), nullable=False, index=True)
    file_md5 = Column(String(32), default="")
    created_at = Column(DateTime, server_default=func.now())


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(String(32), primary_key=True, default=_new_uuid)
    paper_id = Column(String(32), nullable=False)
    problem = Column(Text, default="")
    conclusion = Column(Text, default="")
    conditions = Column(Text, default="")
    innovation = Column(Text, default="")
    paper_type = Column(String(100), default="")
    full_text = Column(LONGTEXT, default="")
    model = Column(String(100), default="")
    tokens = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(32), primary_key=True, default=_new_uuid)
    paper_id = Column(String(32), nullable=False)
    session_id = Column(String(32), nullable=True, default=None)
    role = Column(String(20), nullable=False)
    content = Column(LONGTEXT, nullable=False)
    tokens = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(32), primary_key=True, default=_new_uuid)
    paper_id = Column(String(32), nullable=True, default=None)
    knowledge_base_id = Column(String(32), nullable=True, default=None, index=True)
    title = Column(String(300), default="")
    created_at = Column(DateTime, server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(32), primary_key=True, default=_new_uuid)
    session_id = Column(String(32), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(LONGTEXT, nullable=False)
    tokens = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class Extraction(Base):
    __tablename__ = "extractions"

    id = Column(String(32), primary_key=True, default=_new_uuid)
    paper_id = Column(String(32), nullable=False)
    type = Column(String(50), nullable=False)
    content = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
