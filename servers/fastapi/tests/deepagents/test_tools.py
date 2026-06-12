from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from services.deepagents.schemas import SlidePlan
from services.deepagents.tools import (
    _build_single_file_context,
    _build_single_file_path_context,
    _validate_path_safe,
    build_agent_file_context,
    choose_deterministic_layout,
)


class _FakeLayout:
    def __init__(self, id: str, name: str = "", description: str = ""):
        self.id = id
        self.name = name
        self.description = description


class TestChooseDeterministicLayout:
    def test_valid_index(self) -> None:
        layouts = [_FakeLayout("a"), _FakeLayout("b"), _FakeLayout("c")]
        idx = choose_deterministic_layout(
            available_layouts=layouts,
            requested_layout_index=1,
        )
        assert idx == 1

    def test_invalid_index_high(self) -> None:
        layouts = [_FakeLayout("a"), _FakeLayout("b")]
        slide = SlidePlan(
            index=0,
            title="Test",
            purpose="title",
            main_message="Hello",
            content_density="low",
            visual_intent="simple",
            preferred_layout_tags=["title"],
        )
        idx = choose_deterministic_layout(
            available_layouts=layouts,
            slide_plan=slide,
            requested_layout_index=5,
        )
        assert idx == 0

    def test_invalid_index_negative(self) -> None:
        layouts = [_FakeLayout("a"), _FakeLayout("data-chart")]
        slide = SlidePlan(
            index=0,
            title="Test",
            purpose="data",
            main_message="Stats",
            content_density="medium",
            visual_intent="chart",
        )
        idx = choose_deterministic_layout(
            available_layouts=layouts,
            slide_plan=slide,
            requested_layout_index=-1,
        )
        assert idx == 1

    def test_invalid_index_with_matching_tags(self) -> None:
        layouts = [
            _FakeLayout("agenda"),
            _FakeLayout("content"),
            _FakeLayout("data-chart"),
        ]
        slide = SlidePlan(
            index=0,
            title="Revenue",
            purpose="data",
            main_message="Q4 revenue up",
            content_density="high",
            visual_intent="chart",
            preferred_layout_tags=["chart", "data"],
        )
        idx = choose_deterministic_layout(
            available_layouts=layouts,
            slide_plan=slide,
            requested_layout_index=10,
        )
        assert idx == 2

    def test_invalid_index_with_no_tags_match_by_purpose(self) -> None:
        layouts = [
            _FakeLayout("title-slide"),
            _FakeLayout("text-page"),
            _FakeLayout("side-by-side"),
        ]
        slide = SlidePlan(
            index=0,
            title="Comparison",
            purpose="comparison",
            main_message="A vs B",
            content_density="medium",
            visual_intent="side-by-side",
        )
        idx = choose_deterministic_layout(
            available_layouts=layouts,
            slide_plan=slide,
            requested_layout_index=10,
        )
        assert idx == 2

    def test_empty_layout_list(self) -> None:
        idx = choose_deterministic_layout(
            available_layouts=[],
            requested_layout_index=None,
        )
        assert idx == 0

    def test_no_slide_plan_fallback(self) -> None:
        layouts = [_FakeLayout("a"), _FakeLayout("b")]
        idx = choose_deterministic_layout(
            available_layouts=layouts,
            slide_plan=None,
            requested_layout_index=None,
        )
        assert idx == 0

    def test_deterministic_same_input_same_output(self) -> None:
        layouts = [_FakeLayout("a"), _FakeLayout("b"), _FakeLayout("c")]
        slide = SlidePlan(
            index=0,
            title="Test",
            purpose="insight",
            main_message="Key insight",
            content_density="low",
            visual_intent="big text",
            preferred_layout_tags=["insight"],
        )
        idx1 = choose_deterministic_layout(
            available_layouts=layouts,
            slide_plan=slide,
            requested_layout_index=10,
        )
        idx2 = choose_deterministic_layout(
            available_layouts=layouts,
            slide_plan=slide,
            requested_layout_index=10,
        )
        assert idx1 == idx2


class TestBuildAgentFileContext:
    def test_none_files(self) -> None:
        ctx = build_agent_file_context(None)
        assert ctx == []

    def test_empty_list(self) -> None:
        ctx = build_agent_file_context([])
        assert ctx == []

    def test_dict_file_list(self) -> None:
        files = [
            {"id": "f1", "filename": "report.pdf", "mime_type": "application/pdf"},
            {
                "id": "f2",
                "filename": "data.xlsx",
                "mime_type": "application/vnd.ms-excel",
            },
        ]
        ctx = build_agent_file_context(files)
        assert len(ctx) == 2
        assert ctx[0]["file_id"] == "f1"
        assert ctx[0]["safe_ref"] == "input://f1"
        assert ctx[1]["filename"] == "data.xlsx"

    def test_file_with_summary(self) -> None:
        files = [
            {
                "id": "f1",
                "filename": "research.md",
                "mime_type": "text/markdown",
                "summary": "Key points about AI trends",
            }
        ]
        ctx = build_agent_file_context(files)
        assert ctx[0]["summary"] == "Key points about AI trends"

    def test_file_without_id(self) -> None:
        files = [
            {"name": "readme.txt", "mime": "text/plain"},
        ]
        ctx = build_agent_file_context(files)
        assert len(ctx) == 1
        assert ctx[0]["file_id"] == "readme.txt"

    def test_path_traversal_detected(self) -> None:
        with pytest.raises(ValueError, match="Path traversal"):
            _validate_path_safe("/inputs/../../etc/passwd")

    def test_safe_path_passes(self) -> None:
        _validate_path_safe("/workspace/data.txt")
        _validate_path_safe("/outputs/result.json")
        _validate_path_safe("/memories/prefs.md")
        _validate_path_safe("/inputs/report.pdf")

    def test_missing_file_produces_warning(self) -> None:
        ctx = _build_single_file_path_context("/nonexistent/file.pdf")
        assert ctx is not None
        assert "warning" in ctx

    def test_path_traversal_in_file_path(self) -> None:
        with pytest.raises(ValueError):
            _validate_path_safe("/inputs/foo/../../bar.txt")

    def test_path_outside_allowed_boundary_rejected(self) -> None:
        with pytest.raises(ValueError, match="outside allowed virtual boundaries"):
            _validate_path_safe("/etc/passwd")

    def test_http_url_passes_validation(self) -> None:
        _validate_path_safe("https://example.com/file.pdf")

    def test_windows_absolute_path_c_drive_rejected(self) -> None:
        with pytest.raises(ValueError, match="Windows absolute path"):
            _validate_path_safe("C:/Users/foo/bar.txt")

    def test_windows_absolute_path_backslash_rejected(self) -> None:
        with pytest.raises(ValueError, match="Windows absolute path"):
            _validate_path_safe("D:\\Users\\foo\\bar.txt")

    def test_windows_absolute_path_lowercase_drive_rejected(self) -> None:
        with pytest.raises(ValueError, match="Windows absolute path"):
            _validate_path_safe("e:/temp/file.pdf")
