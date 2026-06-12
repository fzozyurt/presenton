# TASK 14 — Add memory seed files

## Goal

Give the agent a safe initial memory structure so it does not invent its own memory format.

## File

`services/deepagents/memory.py`

## Required seed files

The agent should initialize these files when memory mode allows it and they do not exist:

```text
/memories/presentation_preferences.md
/memories/design_patterns.md
/memories/failure_lessons.md
```

## Seed content

Use the files from the `memory_seeds/` folder in this prompt package.

## Rules

1. Memory mode `off`: do not create or update memory.
2. Memory mode `review`: do not edit `/memories/**`; create a proposed patch under `/outputs/...`.
3. Memory mode `auto`: initialize missing memory seed files.
4. Never overwrite existing memory blindly.
5. Prefer append or careful section update.
6. Keep user-scoped memory isolated by user.
7. Do not store secrets, API keys, or raw uploaded documents.

## Implement helpers

```python
async def ensure_memory_seed_files(...)
def get_memory_seed_content(file_name: str) -> str
def build_memory_update_instruction(auto_mode: bool, memory_mode: str) -> str
```

## Acceptance criteria

- Missing memory files can be seeded in auto mode.
- Existing memory is not overwritten.
- Review mode produces patch instructions only.
- Off mode disables memory writes.
