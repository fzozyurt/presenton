# TASK 17 — Harden file input strategy

## Goal

Make uploaded file handling safe and useful for the Deep Agent.

## Rules

1. Uploaded/input files are read-only.
2. Do not pass raw unrestricted filesystem paths to the agent.
3. Pass sanitized metadata:
   - file id
   - original filename
   - mime type
   - extracted text summary if available
   - safe internal reference
4. Do not prompt-inject raw document text blindly.
5. For long documents, pass summaries and relevant excerpts.
6. Track evidence with `EvidenceItem.source_ref`.
7. Do not store raw uploaded documents in memory.
8. Do not write to `/inputs/**`.

## Suggested helper

```python
def build_agent_file_context(files: list) -> list[dict]:
    ...
```

Expected output:

```json
[
  {
    "file_id": "...",
    "filename": "...",
    "mime_type": "...",
    "summary": "...",
    "safe_ref": "input://..."
  }
]
```

## Acceptance criteria

- File path traversal is not possible.
- Missing files produce readable errors.
- Agent receives sanitized file context.
- Evidence items can point to file references.
- Memory never stores raw file content.
