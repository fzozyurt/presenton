from __future__ import annotations

from typing import Any, Optional

from .config import DeepAgentsSettings


def _build_user_namespace(user_id: Optional[str] = None) -> tuple[str, str, str]:
    if user_id is not None:
        return ("presentation-agent", "user", str(user_id))
    return ("presentation-agent", "user", "anonymous")


def build_deepagents_backend(
    settings: Optional[DeepAgentsSettings] = None,
    user_id: Optional[str] = None,
) -> Any:
    """
    Build a composite backend for Deep Agents.

    Routing:
    - default (thread-scoped): StateBackend
    - /memories/: StoreBackend (long-term)

    Returns a backend object compatible with create_deep_agent(backend=...).
    """
    try:
        from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
    except ImportError:
        from deepagents.backends.composite import CompositeBackend
        from deepagents.backends.state import StateBackend
        from deepagents.backends.store import StoreBackend

    namespace = _build_user_namespace(user_id)

    state_backend = StateBackend()
    store_backend = StoreBackend(namespace=namespace)

    backend = CompositeBackend(
        default=state_backend,
        routes={"/memories/": store_backend},
    )

    return backend
