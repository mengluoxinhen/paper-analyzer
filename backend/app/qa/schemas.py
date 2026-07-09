from pydantic import BaseModel


class QARequest(BaseModel):
    question: str


class QARebuildResponse(BaseModel):
    ok: bool
    indexed_count: int = 0
    message: str = ""
