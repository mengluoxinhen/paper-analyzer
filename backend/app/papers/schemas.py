from datetime import datetime
from pydantic import BaseModel


# ── KnowledgeBase ──
class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str = ""


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    user_id: str | None = None
    is_shared: bool = False
    paper_count: int = 0
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Review ──
class ReviewRejectRequest(BaseModel):
    comment: str = ""


class ReviewPaperItem(BaseModel):
    id: str
    title: str
    filename: str
    created_at: datetime
    is_duplicate: bool = False
    duplicate_title: str = ""


class ReviewListResponse(BaseModel):
    papers: list[ReviewPaperItem]
    total: int


# ── Folder ──
class FolderCreate(BaseModel):
    name: str
    parent_id: str | None = None
    knowledge_base_id: str


class FolderListResponse(BaseModel):
    folders: list['FolderResponse'] = []
    uncategorized_count: int = 0


class FolderResponse(BaseModel):
    id: str
    name: str
    parent_id: str | None = None
    knowledge_base_id: str | None = None
    paper_count: int = 0
    children: list["FolderResponse"] = []
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Tag ──
class TagCreate(BaseModel):
    name: str
    knowledge_base_id: str


class TagResponse(BaseModel):
    id: str
    name: str
    knowledge_base_id: str | None = None
    paper_count: int = 0
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Paper ──
class PaperCreate(BaseModel):
    title: str = ""


class TagItem(BaseModel):
    id: str
    name: str
    model_config = {"from_attributes": True}


class PaperResponse(BaseModel):
    id: str
    title: str
    filename: str
    pdf_path: str = ""
    status: str
    folder_id: str | None = None
    folder_name: str | None = None
    knowledge_base_id: str | None = None
    review_status: str = "none"
    file_md5: str = ""
    review_comment: str = ""
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
    folder_id: str | None = None


class PaperTagUpdate(BaseModel):
    tag_ids: list[str] = []



# ── Summary ──
class SummaryResponse(BaseModel):
    id: str
    paper_id: str
    problem: str = ""
    conclusion: str = ""
    conditions: str = ""
    full_text: str = ""
    innovation: str = ""
    paper_type: str = ""
    model: str = ""
    tokens: int = 0
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


# ── Conversation ──
class ConversationResponse(BaseModel):
    id: str
    paper_id: str
    role: str
    content: str
    tokens: int
    created_at: datetime
    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str


class CompareRequest(BaseModel):
    paper_ids: list[str]


class ExtractRequest(BaseModel):
    types: list[str] = ["figures", "tables", "references", "formulas"]


class ExtractionResponse(BaseModel):
    id: str
    paper_id: str
    type: str
    content: dict
    created_at: datetime
    model_config = {"from_attributes": True}
