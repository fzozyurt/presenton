# TASK 02 — Create the Deep Agents module structure

## Goal

Create an isolated Deep Agents integration module instead of spreading orchestration code across existing endpoint files.

## Create this module structure

```text
services/deepagents/
  __init__.py
  config.py
  schemas.py
  prompts.py
  backend.py
  permissions.py
  mcp.py
  tools.py
  agent_factory.py
  runner.py
  jobs.py
  memory.py
  auto_mode.py
  errors.py
```

Use the existing project package style. If the project keeps service code elsewhere, place this module in the equivalent service layer.

## Responsibilities

### config.py

Read and validate Deep Agents settings.

### schemas.py

Hold Pydantic schemas for deck planning, quality review, and run results.

### prompts.py

Hold supervisor and subagent prompts.

### backend.py

Create the Deep Agents backend and state/memory routing.

### permissions.py

Create filesystem permission rules.

### mcp.py

Load presentation API tools through MCP.

### tools.py

Hold local utility tools if needed.

### agent_factory.py

Build the Deep Agent.

### runner.py

Expose the async entrypoint used by endpoints, jobs, and cron.

### jobs.py

Handle database run state helpers and background worker logic.

### memory.py

Handle memory seed files, memory update instructions, and patch validation.

### auto_mode.py

Expose future cron-safe auto mode entrypoints.

### errors.py

Hold custom exceptions.

## Rules

- Keep imports lazy where possible.
- Avoid circular imports.
- Do not import endpoint modules from this service module.
- Do not import request-scoped database sessions here.
- No side effects at import time.

## Acceptance criteria

- All files exist.
- Each file can be imported.
- No circular import occurs.
- Legacy behavior is untouched.
