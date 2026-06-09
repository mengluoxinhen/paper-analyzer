from datetime import datetime
from pydantic import BaseModel


# ── Folder ──
class FolderCreate(BaseModel):
    name: str
    parent_id: int | None = None


class FolderListResponse(BaseModel):
    folders: list['FolderResponse'] = []
    uncategorized_count: int = 0


class FolderResponse(BaseModel):
    id: int
    name: str
    parent_id: int | None = None
    paper_count: int = 0
    children: list["FolderResponse"] = []
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Tag ──
class TagCreate(BaseModel):
    name: str


class TagResponse(BaseModel):
    id: int
    name: str
    paper_count: int = 0
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Paper ──
class PaperCreate(BaseModel):
    title: str = ""


class TagItem(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class PaperResponse(BaseModel):
    id: int
    title: str
    filename: str
    md_path: str
    json_path: str
    pdf_path: str = ""
    status: str
    folder_id: int | None = None
    folder_name: str | None = None
    tags: list[TagItem] = []
    created_at: datetime
    model_config = {"from_attributes": True}


class PaperDetail(PaperResponse):
    md_content: str | None = ""
    model_config = {"from_attributes": True}


class PaperListResponse(BaseModel):
    papers: list[PaperResponse]
    total: int


class PaperMoveRequest(BaseModel):
    folder_id: int | None = None  # None means move to uncategorized


class PaperTagUpdate(BaseModel):
    tag_ids: list[int] = []


# ── Summary ──
class SummaryResponse(BaseModel):
    id: int
    paper_id: int
    problem: str = ""
    conclusion: str = ""
    conditions: str = ""
    full_text: str = ""
    model: str = ""
    tokens: int = 0
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


# ── Conversation ──
class ConversationResponse(BaseModel):
    id: int
    paper_id: int
    role: str
    content: str
    tokens: int
    created_at: datetime
    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str


class CompareRequest(BaseModel):
    paper_ids: list[int]


class ExtractRequest(BaseModel):
    types: list[str] = ["figures", "tables", "references", "formulas"]


class ExtractionResponse(BaseModel):
    id: int
    paper_id: int
    type: str
    content: dict
    created_at: datetime
    model_config = {"from_attributes": True}