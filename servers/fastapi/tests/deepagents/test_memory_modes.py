from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from services.deepagents.config import DeepAgentsSettings

import pytest

from services.deepagents.memory import (
    build_memory_update_instruction,
    ensure_memory_seed_files,
    validate_memory_patch,
    validate_memory_update,
)


class TestBuildMemoryUpdateInstruction:
    def test_off_mode(self) -> None:
        instruction = build_memory_update_instruction(
            auto_mode=False, memory_mode="off", presentation_id="pres-1"
        )
        assert "off" in instruction
        assert "Do not read or write" in instruction

    def test_review_mode(self) -> None:
        instruction = build_memory_update_instruction(
            auto_mode=False, memory_mode="review", presentation_id="pres-1"
        )
        assert "review" in instruction
        assert "memory_patch.md" in instruction

    def test_auto_mode_with_auto_flag(self) -> None:
        instruction = build_memory_update_instruction(
            auto_mode=True, memory_mode="auto", presentation_id="pres-1"
        )
        assert "auto" in instruction
        assert "cron/auto-mode" not in instruction
        assert "read and write /memories" in instruction

    def test_auto_mode_without_auto_flag(self) -> None:
        instruction = build_memory_update_instruction(
            auto_mode=False, memory_mode="auto", presentation_id="pres-1"
        )
        assert "auto" in instruction
        assert "not a cron/auto-mode" in instruction

    def test_unknown_mode_defaults_to_review(self) -> None:
        instruction = build_memory_update_instruction(
            auto_mode=False, memory_mode="unknown", presentation_id="pres-1"
        )
        assert "Unknown" in instruction


class TestValidateMemoryUpdate:
    def test_clean_content_passes(self) -> None:
        warnings = validate_memory_update(
            "preferences.md", "User prefers dark themes with large fonts."
        )
        assert warnings == []

    def test_forbidden_pattern_detected(self) -> None:
        warnings = validate_memory_update("secrets.md", "my api_key is sk-abc123")
        assert len(warnings) > 0
        assert any("sk-" in w for w in warnings)

    def test_large_content_warns(self) -> None:
        large = "x" * 100_001
        warnings = validate_memory_update("big.md", large)
        assert any("large" in w for w in warnings)


class TestValidateMemoryPatch:
    def test_empty_patch(self) -> None:
        issues = validate_memory_patch("")
        assert len(issues) > 0
        assert "empty" in issues[0]

    def test_clean_patch(self) -> None:
        issues = validate_memory_patch(
            "# Preferences\n\nUser prefers simple layouts.\n"
        )
        assert issues == []

    def test_api_key_rejected(self) -> None:
        issues = validate_memory_patch("The user's API key is sk-proj-abc123.")
        assert any("forbidden" in i.lower() for i in issues)

    def test_uncertain_claim_rejected(self) -> None:
        issues = validate_memory_patch(
            "I think the user might prefer red themes, but I'm uncertain."
        )
        assert any("uncertain" in i.lower() for i in issues)

    def test_large_patch_rejected(self) -> None:
        large = "line\n" * 5 + "x" * 200_001
        issues = validate_memory_patch(large)
        assert any("large" in i.lower() for i in issues)

    def test_email_address_rejected(self) -> None:
        issues = validate_memory_patch(
            "Contact user at john.doe@example.com for preferences."
        )
        assert any("email" in i.lower() for i in issues)

    def test_ssn_pattern_rejected(self) -> None:
        issues = validate_memory_patch("SSN: 123-45-6789")
        assert any("personal data" in i.lower() or "ssn" in i.lower() for i in issues)

    def test_valid_preferences_passes(self) -> None:
        issues = validate_memory_patch(
            "## User Preferences\n"
            "- Preferred language: English\n"
            "- Preferred tone: Professional\n"
            "- Preferred template: pitch-deck\n"
            "- Slide density: Low to medium\n"
        )
        assert issues == []


class TestEnsureMemorySeedFiles:
    def test_off_mode_skips(self) -> None:
        async def _run():
            return await ensure_memory_seed_files(
                memories_root="/tmp/memories",
                memory_mode="off",
            )

        result = asyncio.run(_run())
        assert result == []

    def test_review_mode_skips(self) -> None:
        async def _run():
            return await ensure_memory_seed_files(
                memories_root="/tmp/memories",
                memory_mode="review",
                auto_mode=False,
            )

        result = asyncio.run(_run())
        assert result == []


class TestRunMemoryConsolidate:
    def test_skips_direct_filesystem_seeding(self) -> None:
        from services.deepagents.auto_mode import run_memory_consolidate

        async def _run():
            return await run_memory_consolidate(
                user_id=None,
                auto_mode=True,
                memory_mode="auto",
                dry_run=False,
            )

        with (
            patch(
                "services.deepagents.auto_mode._try_acquire_lock",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "services.deepagents.auto_mode._release_lock",
                new=AsyncMock(),
            ),
        ):
            result = asyncio.run(_run())
        assert result["status"] == "completed"
        assert result["memory_files_checked"] == []
        assert result["memory_files_created"] == []
        assert "not yet implemented" in result["message"]

    def test_off_mode_skips(self) -> None:
        from services.deepagents.auto_mode import run_memory_consolidate

        async def _run():
            return await run_memory_consolidate(
                user_id=None,
                auto_mode=True,
                memory_mode="off",
            )

        result = asyncio.run(_run())
        assert result["status"] == "skipped"

    def test_review_mode_skips(self) -> None:
        from services.deepagents.auto_mode import run_memory_consolidate

        async def _run():
            return await run_memory_consolidate(
                user_id=None,
                auto_mode=True,
                memory_mode="review",
            )

        result = asyncio.run(_run())
        assert result["status"] == "skipped"

    def test_dry_run_returns_without_side_effects(self) -> None:
        from services.deepagents.auto_mode import run_memory_consolidate

        async def _run():
            return await run_memory_consolidate(
                user_id=None,
                auto_mode=True,
                memory_mode="auto",
                dry_run=True,
            )

        result = asyncio.run(_run())
        assert result["status"] == "dry_run"
