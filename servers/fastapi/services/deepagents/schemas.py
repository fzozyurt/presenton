from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class DeckBrief(BaseModel):
    topic: str
    audience: Optional[str] = None
    goal: str
    language: Optional[str] = None
    tone: str = "default"
    verbosity: str = "standard"
    key_message: str
    constraints: list[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    id: str
    source_type: Literal[
        "user_prompt", "uploaded_file", "web", "memory", "presentation_engine"
    ]
    source_ref: Optional[str] = None
    title: Optional[str] = None
    excerpt: str
    confidence: float = Field(ge=0, le=1)


class SlidePlan(BaseModel):
    index: int
    title: str
    purpose: Literal[
        "title",
        "agenda",
        "problem",
        "context",
        "insight",
        "data",
        "comparison",
        "process",
        "solution",
        "case_study",
        "recommendation",
        "closing",
    ]
    main_message: str
    content_density: Literal["low", "medium", "high"]
    visual_intent: str
    preferred_layout_tags: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    image_brief: Optional[str] = None
    chart_brief: Optional[str] = None
    speaker_note_brief: Optional[str] = None


class DesignSystem(BaseModel):
    theme_name: str
    mood: str
    color_intent: str
    typography_intent: str
    spacing_intent: str
    image_style: str
    chart_style: str
    do: list[str] = Field(default_factory=list)
    dont: list[str] = Field(default_factory=list)


class DeckPlan(BaseModel):
    brief: DeckBrief
    design: DesignSystem
    evidence: list[EvidenceItem] = Field(default_factory=list)
    slides: list[SlidePlan]


class SlideQualityIssue(BaseModel):
    slide_index: int
    severity: Literal["low", "medium", "high"]
    category: Literal[
        "narrative",
        "factuality",
        "layout",
        "visual_density",
        "readability",
        "missing_evidence",
        "schema",
        "export",
        "memory",
    ]
    issue: str
    suggested_fix: str


class DeckQualityReport(BaseModel):
    score: int = Field(ge=0, le=100)
    passed: bool
    issues: list[SlideQualityIssue] = Field(default_factory=list)
    summary: str


class DeepAgentRunResult(BaseModel):
    presentation_id: str
    thread_id: str
    status: Literal["completed", "failed", "partial"]
    deck_plan: Optional[DeckPlan] = None
    quality_report: Optional[DeckQualityReport] = None
    presentation_path: Optional[str] = None
    edit_path: Optional[str] = None
    export_path: Optional[str] = None
    memory_updates: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: Optional[str] = None
