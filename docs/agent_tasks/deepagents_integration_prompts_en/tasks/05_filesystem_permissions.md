# TASK 05 — Add filesystem permissions

## Goal

Prevent the agent from writing to unsafe paths while allowing controlled workspace, output, and memory behavior.

## File

`services/deepagents/permissions.py`

## Required permission policy

Path rules:

```text
/inputs/**      read only
/workspace/**   read/write
/outputs/**     read/write
/memories/**    depends on memory mode
/secrets/**     no write
/.env*          no write
/config/**      no write unless explicitly needed
```

Default write behavior must be deny.

## Memory mode behavior

### off

- No memory writes.
- Memory reads may also be disabled by agent factory if desired.

### review

- Do not write to `/memories/**`.
- Write a proposed memory patch under `/outputs/{presentation_id}/memory_patch.md`.

### auto

- Allow safe writes under `/memories/**`.
- Still deny secrets and source code writes.

## Implement

```python
def build_filesystem_permissions(memory_mode: str):
    """
    Return a permissions object/list compatible with create_deep_agent(..., permissions=...).

    memory_mode values:
    - off
    - review
    - auto
    """
```

If the installed Deep Agents version expects a slightly different permissions API, adapt this function while preserving the policy.

## Acceptance criteria

- `/inputs/a.txt` cannot be written.
- `/workspace/a.txt` can be written.
- `/outputs/a.json` can be written.
- `/memories/a.md` can be written only in `auto` mode.
- Unsafe paths cannot be written.
- Unknown paths default to write deny.
