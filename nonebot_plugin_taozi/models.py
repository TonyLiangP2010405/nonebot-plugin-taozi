from typing import Literal

from pydantic import BaseModel, Field

Confidence = Literal["高", "中", "低"]
SubjectType = Literal["水友立场", "主播状态", "社区造词", "含义待核实"]


class EvidenceSource(BaseModel):
    title: str = Field(min_length=1)
    url: str = Field(pattern=r"^https://")
    note: str | None = None


class LexiconEntry(BaseModel):
    term: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    meaning: str = Field(min_length=1)
    subject: SubjectType
    confidence: Confidence
    boundary: str = Field(min_length=1)
    verified_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    sources: list[EvidenceSource] = Field(min_length=1)


class PersistedState(BaseModel):
    version: Literal[1] = 1
    disabled_groups: set[str] = Field(default_factory=set)
    self_colors: dict[str, dict[str, str]] = Field(default_factory=dict)

