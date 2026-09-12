from typing import Literal
from pydantic import BaseModel, Field, model_validator


class Location(BaseModel):
    file: str
    page: int | None = Field(default=None, ge=1)
    slide: int | None = Field(default=None, ge=1)
    section: str | None = None

    @model_validator(mode='after')
    def exact_location(self):
        if sum(v is not None for v in (self.page, self.slide, self.section)) != 1:
            raise ValueError('Exactly one page, slide or section is required')
        return self


class Question(BaseModel):
    id: str
    question: str = Field(min_length=8)
    type: Literal['single_doc', 'multi_doc', 'unsupported']
    answerable: bool
    expected_sources: list[Location] = Field(default_factory=list)
    expected_keywords: list[str] = Field(default_factory=list)
    rationale: str
    verification: Literal['draft', 'human_verified', 'synthetic_authored'] = 'draft'
    verified_by: str | None = None
    verified_at: str | None = None

    @model_validator(mode='after')
    def coherent(self):
        docs = {s.file for s in self.expected_sources}
        if self.answerable != (self.type != 'unsupported'):
            raise ValueError('Answerability conflicts with question type')
        if self.type == 'single_doc' and len(docs) != 1:
            raise ValueError('Single-document question needs exactly one document')
        if self.type == 'multi_doc' and len(docs) < 2:
            raise ValueError('Multi-document question requires two DIFFERENT documents')
        if not self.answerable and self.expected_sources:
            raise ValueError('Unsupported question must have no expected answer sources')
        if self.answerable and not self.expected_keywords:
            raise ValueError('Answerable questions require expected answer keywords')
        if self.verification == 'human_verified' and not (self.verified_by and self.verified_at):
            raise ValueError('Human verification needs reviewer and timestamp')
        return self


def validate_dataset(rows, official=True):
    questions = [Question.model_validate(r) for r in rows]
    if len({q.id for q in questions}) != len(questions):
        raise ValueError('Duplicate question IDs')
    for kind in ('single_doc', 'multi_doc', 'unsupported'):
        if sum(q.type == kind for q in questions) != 10:
            raise ValueError('Dataset must contain exactly 10 single, 10 multi, and 10 unsupported questions')
    if official and any(q.verification != 'human_verified' for q in questions):
        raise ValueError('Official evaluation requires human-verified labels. Use --allow-draft for clearly labeled diagnostics only.')
    return questions
