# TASK 11 — Integrate FastAPI endpoints behind feature flags

## Goal

Connect the Deep Agents runner to existing presentation generation endpoints without breaking legacy behavior.

## Files to inspect or update

- Presentation generation endpoint file
- Settings/config module
- Dependency/session helpers
- Route registration if needed

## Required behavior

### Synchronous generation endpoint

If `PRESENTATION_ORCHESTRATOR=legacy`:

- Run the existing legacy handler exactly as before.

If `PRESENTATION_ORCHESTRATOR=deepagents`:

- Create a `thread_id`.
- Call `await run_deepagents_presentation_generation(...)`.
- Return a response compatible with the existing endpoint where possible.
- Include Deep Agents result metadata when safe.

### Asynchronous generation endpoint

If `PRESENTATION_ORCHESTRATOR=legacy`:

- Preserve existing behavior.

If `PRESENTATION_ORCHESTRATOR=deepagents`:

- Create a Deep Agent run record.
- Start a background job using only serializable inputs.
- Do not pass request-scoped database session objects to the background job.
- Return run id and status URL.

### New status endpoint

Add:

```text
GET /presentation/deepagents/status/{run_id}
```

This endpoint should return:

```json
{
  "run_id": "...",
  "presentation_id": "...",
  "thread_id": "...",
  "status": "...",
  "step": "...",
  "message": "...",
  "output_snapshot": {},
  "error": {}
}
```

## Acceptance criteria

- Legacy mode behavior remains unchanged.
- Deep Agents sync endpoint uses async runner.
- Deep Agents async endpoint returns quickly.
- Background job receives only serializable inputs.
- Status endpoint reads from the new run state table.
- No branch or repository metadata is added.
