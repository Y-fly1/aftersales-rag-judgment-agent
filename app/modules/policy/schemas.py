from datetime import date

from pydantic import BaseModel, ConfigDict


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_no: str
    title: str
    category: str
    scope: str | None = None
    effective_date: date | None = None
    status: str
    summary: str | None = None
    highlights: list[str] = []


class PolicyCategoryStat(BaseModel):
    category: str
    count: int


class PolicyArticle(BaseModel):
    """政策条款片段"""

    section_path: list[str]
    content: str
