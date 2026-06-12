# TASK 10 — Add database job state model

## Goal

Track Deep Agents runs in the database so async endpoints, background workers, UI, and future cron jobs can inspect status.

## Add a database model

Create a model equivalent to:

```python
class DeepAgentPresentationRunModel(SQLModel, table=True):
    __tablename__ = "deepagent_presentation_runs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    presentation_id: uuid.UUID = Field(index=True)
    thread_id: str = Field(index=True)
    user_id: str | None = Field(default=None, index=True)

    status: str = Field(default="pending", index=True)
    step: str | None = None
    message: str | None = None

    auto_mode: bool = False
    memory_mode: str = "review"

    input_snapshot: dict | None = Field(default=None, sa_column=Column(JSON))
    output_snapshot: dict | None = Field(default=None, sa_column=Column(JSON))
    error: dict | None = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
```

Adapt imports and JSON column style to the existing database layer.

## Add helper functions

In `services/deepagents/jobs.py` implement:

```python
async def create_deepagent_run(...)
async def mark_run_started(...)
async def mark_run_step(...)
async def mark_run_completed(...)
async def mark_run_failed(...)
async def get_run_status(...)
```

Each helper should accept an async database session from the caller.

## Rules

- Do not store secrets in snapshots.
- Do not store large file bodies in snapshots.
- Store file metadata, not raw uploaded content.
- Status values should include:
  - `pending`
  - `running`
  - `completed`
  - `failed`
  - `partial`
  - `cancelled`

## Acceptance criteria

- Migration is created if the project uses migrations.
- Run lifecycle works: pending → running → completed.
- Failed runs store error JSON.
- Multiple runs per presentation are allowed.
- `thread_id` and `presentation_id` are indexed.
