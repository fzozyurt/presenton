# TASK 19 — Add tests

## Goal

Test the Deep Agents integration without requiring real LLM or MCP calls in CI.

## Test folder

Create tests under the existing backend test structure, for example:

```text
tests/deepagents/
  test_schemas.py
  test_backend.py
  test_permissions.py
  test_runner_smoke.py
  test_job_state.py
  test_memory_modes.py
```

## Required tests

### test_schemas.py

- Valid `DeckPlan` can be parsed.
- Invalid quality issue severity fails.
- Invalid quality issue category fails.

### test_backend.py

- Backend factory returns an object.
- Missing runtime identity does not crash.

### test_permissions.py

- `/inputs/a.txt` write denied.
- `/workspace/a.txt` write allowed.
- `/outputs/a.json` write allowed.
- `/memories/a.md` denied in off/review.
- `/memories/a.md` allowed in auto.

### test_runner_smoke.py

- Missing `thread_id` fails fast.
- MCP unavailable returns readable failure.
- Mock agent output normalizes into `DeepAgentRunResult`.

### test_job_state.py

- Run lifecycle pending → running → completed.
- Failed run stores error snapshot.

### test_memory_modes.py

- off disables memory writes.
- review creates patch instruction.
- auto allows validated memory update.

## Mocking requirements

- Do not call real LLMs in unit tests.
- Do not require MCP server in CI.
- Mock `create_deck_agent`.
- Mock `agent.ainvoke`.

## Acceptance criteria

- New tests pass.
- Legacy tests still pass.
- CI does not need external model keys.
- CI does not need MCP server.
