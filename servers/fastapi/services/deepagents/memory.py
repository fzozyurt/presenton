from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .errors import MemoryModeError

logger = logging.getLogger(__name__)

_MEMORY_SEEDS: dict[str, str] = {
    "presentation_preferences.md": (
        "# Presentation Preferences\n\n"
        "## Language & Tone\n"
        "- Default language is English.\n"
        "- Default tone is professional.\n\n"
        "## Slide Density\n"
        "- Prefer low-to-medium text density.\n"
        "- One main idea per slide.\n\n"
        "## Export\n"
        "- Default export format is PPTX.\n\n"
        "## Template\n"
        '- Default template is "general".'
    ),
    "design_patterns.md": (
        "# Design Patterns\n\n"
        "## Deck Flow\n"
        "1. Title slide\n"
        "2. Context / background\n"
        "3. Problem or opportunity\n"
        "4. Key insight\n"
        "5. Supporting data or comparison\n"
        "6. Solution or recommendation\n"
        "7. Implementation or process\n"
        "8. Closing\n\n"
        "## Visual Guidelines\n"
        "- Use clear title hierarchy.\n"
        "- Keep each slide focused on one main message.\n"
        "- Use visuals to support evidence, not decoration.\n"
        "- Prefer concise bullet points over long paragraphs.\n\n"
        "## Layout Selection\n"
        "- Match layout purpose to slide purpose.\n"
        "- Use data-focused layouts for evidence slides.\n"
        "- Use comparison layouts for trade-off slides."
    ),
    "failure_lessons.md": (
        "# Failure Lessons\n\n"
        "## Common Issues\n"
        "- Too many slides dilute the main message.\n"
        "- Missing evidence leads to low-confidence claims.\n"
        "- High text density reduces readability.\n"
        "- Export failures often caused by missing session tokens.\n\n"
        "## Prevention\n"
        "- Always create a DeckPlan before generating.\n"
        "- Validate export result before declaring success.\n"
        "- Keep quality review loop active.\n"
        "- Never skip evidence mapping."
    ),
}

_MEMORY_FILES_DIR = "memories"


def get_memory_seed_content(file_name: str) -> str:
    content = _MEMORY_SEEDS.get(file_name)
    if content is None:
        msg = f"Unknown memory seed file: {file_name}"
        raise ValueError(msg)
    return content


def get_known_memory_files() -> list[str]:
    return list(_MEMORY_SEEDS.keys())


def build_memory_update_instruction(
    auto_mode: bool, memory_mode: str, presentation_id: str
) -> str:
    if memory_mode == "off":
        return (
            "Memory mode is off. Do not read or write any memory files. "
            "Do not create /memories/ or /outputs/*/memory_patch.md files."
        )

    if memory_mode == "review":
        return (
            f"Memory mode is review. You may READ /memories/* files. "
            f"Do NOT edit or write files under /memories/. "
            f"Instead, write a proposed memory patch at "
            f"/outputs/{presentation_id}/memory_patch.md "
            f"summarizing any durable lessons worth saving."
        )

    if memory_mode == "auto":
        if auto_mode:
            return (
                f"Memory mode is auto. You may read and write /memories/* files. "
                f"Only save durable, reusable lessons. "
                f"Do NOT store secrets, API keys, raw documents, "
                f"or one-off request details in memory."
            )
        return (
            f"Memory mode is auto but this is not a cron/auto-mode run. "
            f"You may read /memories/* files. "
            f"Write proposed updates to /outputs/{presentation_id}/memory_patch.md "
            f"instead of editing /memories/ directly."
        )

    return (
        f"Unknown memory mode '{memory_mode}'. "
        f"Defaulting to review behavior. "
        f"Read /memories/* files, write proposed patch to "
        f"/outputs/{presentation_id}/memory_patch.md."
    )


async def ensure_memory_seed_files(
    memories_root: str | Path,
    memory_mode: str,
    auto_mode: bool = False,
) -> list[str]:
    if memory_mode == "off":
        logger.debug("Memory mode is off; skipping seed file creation.")
        return []

    if memory_mode == "review" and not auto_mode:
        logger.debug("Memory mode is review; skipping seed file creation.")
        return []

    memories_path = Path(memories_root)
    memories_path.mkdir(parents=True, exist_ok=True)

    created: list[str] = []
    for file_name, content in _MEMORY_SEEDS.items():
        file_path = memories_path / file_name
        if not file_path.exists():
            try:
                file_path.write_text(content, encoding="utf-8")
                created.append(str(file_path))
                logger.info("Created memory seed file: %s", file_path)
            except OSError as exc:
                logger.warning(
                    "Failed to create memory seed file %s: %s", file_path, exc
                )

    return created


def validate_memory_update(file_name: str, content: str) -> list[str]:
    warnings: list[str] = []

    forbidden_patterns = [
        "sk-",
        "api_key",
        "api-key",
        "API_KEY",
        "password",
        "secret",
        "credential",
        "authorization",
        "bearer ",
    ]
    content_lower = content.lower()
    for pattern in forbidden_patterns:
        if pattern.lower() in content_lower:
            warnings.append(
                f"Memory update to {file_name} may contain forbidden content "
                f"(matched pattern: {pattern}). Review before saving."
            )

    if len(content) > 100_000:
        warnings.append(
            f"Memory update to {file_name} is very large "
            f"({len(content)} chars). Consider summarizing."
        )

    return warnings


def validate_memory_patch(patch_text: str) -> list[str]:
    issues: list[str] = []

    if not patch_text or not patch_text.strip():
        issues.append("Memory patch is empty")
        return issues

    forbidden_patterns = [
        "sk-",
        "sk_",
        "api_key",
        "api-key",
        "API_KEY",
        "password",
        "passwd",
        "secret",
        "credential",
        "authorization",
        "bearer ",
        "token ",
        "auth_token",
        "private_key",
        "private-key",
    ]
    text_lower = patch_text.lower()
    for pattern in forbidden_patterns:
        if pattern.lower() in text_lower:
            issues.append(
                f"Patch may contain forbidden content (matched: '{pattern}'). "
                f"Rejected for safety."
            )

    suspicious_markers = [
        "uncertain",
        "unverified",
        "maybe",
        "possibly",
        "i think",
        "i believe",
        "it might",
        "it could be",
    ]
    for marker in suspicious_markers:
        if marker.lower() in text_lower:
            issues.append(
                f"Patch contains uncertain claim marker: '{marker}'. "
                f"Certain claims only."
            )

    if len(patch_text) > 200_000:
        issues.append(
            f"Patch is very large ({len(patch_text)} chars). "
            f"Likely contains raw document dump. Rejected."
        )

    import re

    lines = patch_text.split("\n")
    long_line_count = sum(1 for line in lines if len(line) > 1000)
    if long_line_count > 5:
        issues.append(
            f"Patch contains {long_line_count} very long lines. "
            f"May contain raw document content. Rejected."
        )

    email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    ssn_pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    if re.search(email_pattern, patch_text):
        issues.append("Patch may contain email addresses (personal data). Rejected.")
    if re.search(ssn_pattern, patch_text):
        issues.append("Patch may contain SSN-like patterns (personal data). Rejected.")

    return issues
