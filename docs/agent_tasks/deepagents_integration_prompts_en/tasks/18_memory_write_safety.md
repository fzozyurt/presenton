# TASK 18 — Add memory write safety

## Goal

Allow the system to learn over time without storing unsafe, false, or one-off information.

## File

`services/deepagents/memory.py`

## Implement

```python
def build_memory_update_instruction(auto_mode: bool, memory_mode: str) -> str:
    ...

def validate_memory_patch(patch_text: str) -> list[str]:
    ...
```

## Memory may store

- User's explicitly stated presentation preferences
- Durable deck style preferences
- Successful reusable design patterns
- Failure lessons and fixes
- Language, tone, or export preferences
- Template/layout lessons

## Memory must not store

- API keys or secrets
- Sensitive personal data
- One-off request details
- Raw uploaded document contents
- Unverified factual claims
- Temporary scratch reasoning
- Large generated outputs

## Mode behavior

### off

No memory writes.

### review

Write only a proposed patch under `/outputs/{presentation_id}/memory_patch.md`.

### auto

Write to `/memories/**` only after validation.

## Validation rules

Reject memory patches that appear to contain:

- API keys or tokens
- raw long document dumps
- private credentials
- unrelated personal data
- very large content blocks
- uncertain claims written as facts

## Acceptance criteria

- Review mode does not edit memory.
- Auto mode validates before writing.
- Invalid patches are rejected.
- Memory updates are included in output snapshot or audit log.
