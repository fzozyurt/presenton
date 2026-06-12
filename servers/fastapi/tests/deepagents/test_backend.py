from __future__ import annotations

from unittest.mock import patch

from services.deepagents.backend import (
    _build_user_namespace,
    build_deepagents_backend,
)
from services.deepagents.config import DeepAgentsSettings


def test_build_user_namespace_anonymous() -> None:
    ns = _build_user_namespace(None)
    assert ns == ("presentation-agent", "user", "anonymous")


def test_build_user_namespace_with_user() -> None:
    ns = _build_user_namespace("user-abc")
    assert ns == ("presentation-agent", "user", "user-abc")


def test_backend_factory_returns_object() -> None:
    settings = DeepAgentsSettings()
    backend = build_deepagents_backend(settings=settings, user_id=None)
    assert backend is not None


def test_backend_factory_with_user() -> None:
    settings = DeepAgentsSettings()
    backend = build_deepagents_backend(settings=settings, user_id="test-user")
    assert backend is not None


def test_backend_factory_missing_runtime_identity() -> None:
    settings = DeepAgentsSettings()
    backend = build_deepagents_backend(settings=settings, user_id=None)
    assert backend is not None
