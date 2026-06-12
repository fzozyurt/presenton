from __future__ import annotations

import pytest
from pydantic import ValidationError

from services.deepagents.schemas import (
    DeckBrief,
    DeckPlan,
    DeckQualityReport,
    DesignSystem,
    EvidenceItem,
    SlidePlan,
    SlideQualityIssue,
)


def test_valid_deck_brief() -> None:
    brief = DeckBrief(
        topic="AI in Healthcare",
        audience="Doctors",
        goal="Inform",
        key_message="AI helps",
    )
    assert brief.topic == "AI in Healthcare"
    assert brief.goal == "Inform"


def valid_deck_plan_dict() -> dict:
    return {
        "brief": {
            "topic": "Renewable Energy",
            "goal": "Educate",
            "key_message": "Solar is cheap",
        },
        "design": {
            "theme_name": "green-energy",
            "mood": "optimistic",
            "color_intent": "greens and blues",
            "typography_intent": "clean sans-serif",
            "spacing_intent": "generous",
            "image_style": "photography",
            "chart_style": "clean",
        },
        "slides": [
            {
                "index": 0,
                "title": "Introduction",
                "purpose": "title",
                "main_message": "Welcome",
                "content_density": "low",
                "visual_intent": "hero image",
            }
        ],
    }


def test_valid_deck_plan() -> None:
    plan = DeckPlan(**valid_deck_plan_dict())
    assert len(plan.slides) == 1
    assert plan.brief.topic == "Renewable Energy"


def test_invalid_quality_issue_severity() -> None:
    with pytest.raises(ValidationError):
        SlideQualityIssue(
            slide_index=0,
            severity="critical",
            category="layout",
            issue="Bad",
            suggested_fix="Fix it",
        )


def test_invalid_quality_issue_category() -> None:
    with pytest.raises(ValidationError):
        SlideQualityIssue(
            slide_index=0,
            severity="high",
            category="unknown_category",
            issue="Bad",
            suggested_fix="Fix it",
        )


def test_valid_slide_quality_issue() -> None:
    issue = SlideQualityIssue(
        slide_index=0,
        severity="high",
        category="layout",
        issue="Too much text",
        suggested_fix="Reduce text density",
    )
    assert issue.severity == "high"
    assert issue.category == "layout"


def test_valid_deck_quality_report() -> None:
    report = DeckQualityReport(
        score=85,
        passed=True,
        issues=[
            SlideQualityIssue(
                slide_index=1,
                severity="low",
                category="readability",
                issue="Small font",
                suggested_fix="Increase font size",
            )
        ],
        summary="Good deck with minor issues",
    )
    assert report.score == 85
    assert report.passed is True
    assert len(report.issues) == 1


def test_quality_report_score_out_of_range() -> None:
    with pytest.raises(ValidationError):
        DeckQualityReport(score=150, passed=True, summary="Too high")


def test_evidence_item_defaults() -> None:
    item = EvidenceItem(
        id="ev-1",
        source_type="user_prompt",
        excerpt="Important claim",
        confidence=0.8,
    )
    assert item.source_ref is None
    assert item.title is None


def test_evidence_item_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        EvidenceItem(
            id="ev-2",
            source_type="web",
            excerpt="Bad",
            confidence=2.0,
        )


def test_slide_plan_defaults() -> None:
    plan = SlidePlan(
        index=0,
        title="Test",
        purpose="insight",
        main_message="Key finding",
        content_density="medium",
        visual_intent="chart",
    )
    assert plan.preferred_layout_tags == []
    assert plan.evidence_ids == []
