# TASK 04 — Implement backend and state strategy

## Goal

Set up Deep Agents state, workspace, and long-term memory routing safely.

## File

`services/deepagents/backend.py`

## Required strategy

Use a composite backend:

1. Default backend: thread-scoped state.
2. Long-term memory backend: store backend routed only under `/memories/`.
3. Do not use a real local filesystem backend for the application source tree.
4. Do not let agent writes touch source code, configuration files, or secrets.
5. The first production-safe implementation should use isolated state and store backends.

## Implement

```python
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend


def build_deepagents_backend():
    """
    Return a CompositeBackend.

    Routing:
    - default: StateBackend
    - /memories/: StoreBackend

    The StoreBackend namespace should be user-scoped when a user identity is available.
    If user identity is not available, use a safe anonymous namespace.
    """
```

The runtime object may differ across versions. Handle missing attributes defensively.

Suggested namespace behavior:

```python
("presentation-agent", "user", user_id)
```

Fallback:

```python
("presentation-agent", "user", "anonymous")
```

## Design notes

- `/workspace/` is temporary and thread-scoped.
- `/outputs/` is temporary unless separately persisted by the application.
- `/memories/` is long-term memory.
- `/inputs/` is read-only and should never be written.

## Acceptance criteria

- `build_deepagents_backend()` returns a backend object.
- Missing runtime user identity does not crash.
- Only `/memories/` is routed to long-term store.
- Default state remains thread-scoped.
