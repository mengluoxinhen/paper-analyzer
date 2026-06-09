from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func, Table, UniqueConstraint
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


paper_tags = Table(
    "paper_tags",
    Base.metadata,
    Column("paper_id", Integer, ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Folder(Base):
    __tablename__ = "folders"
    __table_args__ = (UniqueConstraint('name', 'parent_id', name='uq_folder_name_parent'),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    parent_id = Column(Integer, ForeignKey("folders.id", ondelete="CASCADE"), nullable=True, default=None)
    created_at = Column(DateTime, server_default=func.now())

    parent = relationship("Folder", remote_side=[id], back_populates="children")
    children = relationship("Folder", back_populates="parent", cascade="all, delete-orphan", lazy="selectin")
    papers = relationship("Paper", back_populates="folder", cascade="all, delete-orphan")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    papers = relationship("Paper", secondary=paper_tags, back_populates="tags")


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), default="")
    filename = Column(String(500), nullable=False)
    md_path = Column(String(1000), default="")
    pdf_path = Column(String(1000), default="")
    json_path = Column(String(1000), default="")
    md_content = Column(LONGTEXT, default="")
    status = Column(String(50), default="uploaded")
    folder_id = Column(Integer, ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, default=None)
    created_at = Column(DateTime, server_default=func.now())

    folder = relationship("Folder", back_populates="papers")
    tags = relationship("Tag", secondary=paper_tags, back_populates="papers")
    summaries = relationship("Summary", back_populates="paper", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="paper", cascade="all, delete-orphan")
    extractions = relationship("Extraction", back_populates="paper", cascade="all, delete-orphan")


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    problem = Column(Text, default="")
    conclusion = Column(Text, default="")
    conditions = Column(Text, default="")
    full_text = Column(LONGTEXT, default="")
    model = Column(String(100), default="")
    tokens = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    paper = relationship("Paper", back_populates="summaries")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(LONGTEXT, nullable=False)
    tokens = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    paper = relationship("Paper", back_populates="conversations")


class Extraction(Base):
    __tablename__ = "extractions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)
    content = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())

    paper = relationship("Paper", back_populates="extractions")