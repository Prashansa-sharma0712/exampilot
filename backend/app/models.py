from typing import Literal
from pydantic import BaseModel, Field

Status = Literal['ANSWERED', 'PARTIALLY_ANSWERED', 'NOT_COVERED', 'LOW_QUALITY_SOURCE', 'ERROR']
Quality = Literal['HIGH', 'MEDIUM', 'LOW']


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    source_type: str
    page: int | None = None
    slide: int | None = None
    section: str | None = None
    heading: str | None = None
    text: str
    original_asset_path: str
    extraction_quality: Quality = 'HIGH'
    extraction_method: str = 'native'
    topics: list[str] = Field(default_factory=list)

    @property
    def location(self):
        return f'p. {self.page}' if self.page else f'slide {self.slide}' if self.slide else self.section or 'image'


class Claim(BaseModel):
    text: str = Field(min_length=1)
    citations: list[str] = Field(min_length=1)
    quotes: dict[str, str]


class Need(BaseModel):
    need: str
    supported: bool
    citations: list[str] = Field(default_factory=list)


class Answer(BaseModel):
    status: Status
    answer: str
    claims: list[Claim] = Field(default_factory=list)
    coverage: list[Need] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    session_id: str = ''
    resolved_question: str = ''
    mode: str = 'extractive'
    warnings: list[str] = Field(default_factory=list)
    retrieval_ms: float = 0


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    document_id: str | None = None
    source_type: str | None = None
    action: Literal['ask', 'simple', 'compare', 'exam', 'example'] = 'ask'
