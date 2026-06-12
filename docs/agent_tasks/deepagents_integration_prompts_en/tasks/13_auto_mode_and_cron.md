# TASK 13 — Add auto mode and cron entrypoint

## Goal

Prepare the Deep Agents integration for future scheduled execution.

## File

`services/deepagents/auto_mode.py`

## Required modes

### generate

Generate a presentation from a saved request JSON.

### memory_consolidate

Review recent successful and failed runs and update long-term memory with reusable lessons.

### quality_recheck

Re-check a previously generated deck result and produce a new quality report.

## CLI behavior

Support commands equivalent to:

```bash
python -m services.deepagents.auto_mode generate --request-json /path/to/request.json
python -m services.deepagents.auto_mode memory_consolidate --user-id USER_ID
python -m services.deepagents.auto_mode quality_recheck --run-id RUN_ID
```

Also support:

```bash
--dry-run
```

## Auto mode rules

1. Cron uses `auto_mode=true`.
2. Cron uses `memory_mode=auto`, unless `--dry-run` is set.
3. Dry run must never write memory.
4. Auto mode must use locks to avoid duplicate jobs.
5. Do not write user-specific memory into global memory.
6. Only durable, reusable lessons may be saved.

## Lock strategy

Implement one of:

- Database lock table
- Database advisory lock
- Existing application lock mechanism

The lock key should include:

```text
deepagents:{mode}:{user_id_or_global}
```

## Acceptance criteria

- CLI imports successfully.
- Dry run does not modify memory.
- Duplicate cron job attempts are skipped safely.
- Memory consolidation writes only under `/memories/`.
- Errors are logged and stored in run state when relevant.
