from __future__ import annotations

import logging
from typing import Any, Optional

from .schemas import SlidePlan

logger = logging.getLogger(__name__)


def choose_deterministic_layout(
    *,
    available_layouts: list[Any],
    slide_plan: Optional[SlidePlan] = None,
    requested_layout_index: int | None = None,
) -> int:
    if not available_layouts:
        return 0

    if requested_layout_index is not None:
        if 0 <= requested_layout_index < len(available_layouts):
            return requested_layout_index
        logger.debug(
            "Invalid requested layout index %d (max %d); falling back",
            requested_layout_index,
            len(available_layouts) - 1,
        )

    if slide_plan is None:
        return 0

    tags = slide_plan.preferred_layout_tags
    if tags:
        for idx, layout in enumerate(available_layouts):
            layout_id = (
                getattr(layout, "id", None) or getattr(layout, "name", None) or ""
            )
            if any(tag in layout_id for tag in tags):
                return idx
        for idx, layout in enumerate(available_layouts):
            layout_id = (
                getattr(layout, "id", None) or getattr(layout, "name", None) or ""
            )
            layout_desc = getattr(layout, "description", None) or ""
            combined = f"{layout_id} {layout_desc}".lower()
            if any(tag.lower() in combined for tag in tags):
                return idx

    purpose = slide_plan.purpose
    purpose_layout_map: dict[str, list[str]] = {
        "title": ["title", "opener", "cover"],
        "agenda": ["agenda", "overview", "table-of-contents"],
        "problem": ["problem", "challenge", "pain-point"],
        "context": ["context", "background", "text"],
        "insight": ["insight", "highlight", "key-finding"],
        "data": ["data", "chart", "statistics", "numbers"],
        "comparison": ["comparison", "versus", "side-by-side", "before-after"],
        "process": ["process", "timeline", "steps", "flow"],
        "solution": ["solution", "approach", "how-it-works"],
        "case_study": ["case-study", "example", "testimonial"],
        "recommendation": ["recommendation", "next-steps", "call-to-action"],
        "closing": ["closing", "thank-you", "summary"],
    }
    purpose_keywords = purpose_layout_map.get(purpose, [])
    for idx, layout in enumerate(available_layouts):
        layout_id = getattr(layout, "id", None) or getattr(layout, "name", None) or ""
        layout_desc = getattr(layout, "description", None) or ""
        combined = f"{layout_id} {layout_desc}".lower()
        if any(kw.lower() in combined for kw in purpose_keywords):
            return idx

    density = slide_plan.content_density
    if density == "low":
        for idx, layout in enumerate(available_layouts):
            layout_id = (
                getattr(layout, "id", None) or getattr(layout, "name", None) or ""
            )
            layout_desc = getattr(layout, "description", None) or ""
            combined = f"{layout_id} {layout_desc}".lower()
            if any(
                kw in combined
                for kw in ["simple", "minimal", "single", "one", "hero", "big"]
            ):
                return idx
    elif density == "high":
        for idx, layout in enumerate(available_layouts):
            layout_id = (
                getattr(layout, "id", None) or getattr(layout, "name", None) or ""
            )
            layout_desc = getattr(layout, "description", None) or ""
            combined = f"{layout_id} {layout_desc}".lower()
            if any(
                kw in combined
                for kw in ["detailed", "complex", "multi", "bullets", "list"]
            ):
                return idx

    return 0


def build_agent_file_context(files: Any) -> list[dict[str, Any]]:
    if files is None:
        return []

    file_contexts: list[dict[str, Any]] = []

    if isinstance(files, list):
        for item in files:
            ctx = _build_single_file_context(item)
            if ctx is not None:
                file_contexts.append(ctx)
    elif isinstance(files, str):
        ctx = _build_single_file_path_context(files)
        if ctx is not None:
            file_contexts.append(ctx)

    return file_contexts


def _build_single_file_context(item: Any) -> Optional[dict[str, Any]]:
    try:
        file_id = _safe_get(item, "id", None) or _safe_get(item, "file_id", None)
        filename = _safe_get(item, "name", None) or _safe_get(item, "filename", None)
        mime_type = _safe_get(item, "mime_type", None) or _safe_get(item, "mime", None)
        file_path = _safe_get(item, "path", None) or _safe_get(item, "file_path", None)
        summary = _safe_get(item, "summary", None)

        if not filename and file_path:
            from pathlib import Path

            filename = Path(str(file_path)).name

        if not filename:
            filename = "unknown"
        if not mime_type:
            mime_type = "application/octet-stream"
        if not file_id:
            file_id = filename

        if file_path:
            _validate_path_safe(str(file_path))

        return {
            "file_id": str(file_id),
            "filename": str(filename),
            "mime_type": str(mime_type),
            "summary": str(summary) if summary is not None else None,
            "safe_ref": f"input://{file_id}" if file_id else f"input://{filename}",
        }
    except Exception as exc:
        logger.warning("Failed to build file context for item %s: %s", item, exc)
        return None


def _build_single_file_path_context(file_path: str) -> Optional[dict[str, Any]]:
    try:
        from pathlib import Path

        p = Path(file_path)
        if not p.exists():
            logger.warning("File not found: %s", file_path)
            return {
                "file_id": p.name,
                "filename": p.name,
                "mime_type": "application/octet-stream",
                "summary": None,
                "safe_ref": None,
                "warning": f"File not found: {file_path}",
            }

        _validate_path_safe(str(p.resolve()))

        import mimetypes

        mime_type, _ = mimetypes.guess_type(str(p))

        return {
            "file_id": p.name,
            "filename": p.name,
            "mime_type": mime_type or "application/octet-stream",
            "summary": None,
            "safe_ref": f"input://{p.name}",
        }
    except Exception as exc:
        logger.warning("Failed to build file context for path %s: %s", file_path, exc)
        return None


def _validate_path_safe(path: str) -> None:
    normalized = path.replace("\\", "/")
    if ".." in normalized:
        raise ValueError(f"Path traversal detected: {path}")
    if normalized.startswith("/inputs/"):
        return
    if normalized.startswith("/workspace/"):
        return
    if normalized.startswith("/outputs/"):
        return
    if normalized.startswith("/memories/"):
        return
    if "://" in normalized:
        return
    if normalized.startswith("/"):
        raise ValueError(f"Path outside allowed virtual boundaries: {path}")


def _safe_get(obj: Any, attr: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)
