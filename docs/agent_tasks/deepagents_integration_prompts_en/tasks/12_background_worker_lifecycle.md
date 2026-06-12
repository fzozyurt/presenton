# TASK 12 — Add safe background worker lifecycle

## Goal

Run Deep Agents generation in the background without reusing request-scoped resources.

## File

`services/deepagents/jobs.py`

## Implement

```python
async def run_deepagents_generation_job(
    *,
    run_id: str,
    presentation_id: str,
    request_snapshot: dict,
    export_cookie_header: str | None,
):
    ...
```

## Required lifecycle

1. Open a fresh async database session inside the job.
2. Mark run as `running`.
3. Rebuild the request object from `request_snapshot`.
4. Call `run_deepagents_presentation_generation(...)`.
5. On success:
   - status `completed` or `partial`
   - save output snapshot
6. On error:
   - status `failed`
   - save error details
7. Always close the database session.
8. Never leave a run stuck in `running` if an exception occurs.

## Required step names

Use these step labels:

```text
creating_agent
planning
generating
quality_review
exporting
saving_memory
completed
failed
```

## Acceptance criteria

- Worker failures are captured in DB.
- Database session is always closed.
- Multiple jobs can run concurrently.
- No request-scoped session object is passed into this worker.
- Output snapshot is JSON serializable.
