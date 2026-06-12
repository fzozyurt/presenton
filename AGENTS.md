# AGENTS.md

## Project Mission

This project is extending an existing presentation-generation system with a clean LangChain Deep Agents orchestration layer.

The goal is not to rewrite the current presentation engine. The goal is to preserve the existing generation, template, API, MCP, and export flow while adding a safer, more intelligent orchestration layer for planning, file-aware context handling, memory, async execution, background jobs, and future cron automation.

## Primary Architecture

The system should be organized as two layers:

1. **Existing Presentation Engine**
   - Owns current presentation generation.
   - Owns templates and layout rendering.
   - Owns PPTX/PDF export.
   - Owns current API behavior.
   - Must remain backward compatible.

2. **Deep Agents Orchestration Layer**
   - Coordinates planning, evidence mapping, file context, quality review, memory, and auto mode.
   - Uses existing presentation-engine tools instead of rebuilding the engine.
   - Runs behind feature flags.
   - Must be async-safe and cron-safe.
   - Must not break the legacy flow.

Default behavior must remain legacy unless Deep Agents mode is explicitly enabled.

---

## Absolute Rules

1. Do not rewrite the whole project.
2. Do not break legacy presentation generation.
3. Do not remove existing API behavior unless explicitly requested.
4. Do not introduce Agno.
5. Use LangChain Deep Agents only for this integration.
6. Keep all new orchestration code isolated in a dedicated Deep Agents service/module.
7. All Deep Agents execution paths must be async.
8. Background jobs must not reuse request-scoped database sessions.
9. Cron/auto-mode execution must open its own resources and close them safely.
10. User-uploaded files are read-only.
11. Agent workspace files must be isolated from the application source tree.
12. Long-term memory writes must only happen under explicit memory paths.
13. Default memory mode must be `review`, not `auto`.
14. Auto mode must be safe, lock-protected, and suitable for future cron execution.
15. Prefer small, deterministic, schema-driven changes.
16. Do not add broad abstractions before they are needed.
17. Do not store secrets, raw uploaded documents, API keys, or one-off request details in memory.
18. Always maintain compatibility with existing code style, imports, API contracts, and database patterns.

---

## Required Development Flow

For every non-trivial task, follow this order:

1. **Analyze first**
2. **Map affected files**
3. **Use Serena MCP for codebase analysis**
4. **Create a small implementation plan**
5. **Modify the smallest safe set of files**
6. **Run focused tests or import checks**
7. **Report changed files, risks, and follow-up work**

Never start editing before understanding the current structure.

---

## Serena MCP Requirement

Serena MCP must be used as the primary codebase analysis tool whenever available.

Before making structural changes, the agent must use Serena MCP to inspect:

- Existing symbols
- Existing services/modules
- Existing endpoint flow
- Existing database/session patterns
- Existing async/background task patterns
- Existing configuration style
- Existing test style
- Existing MCP integration
- Existing file handling logic

Serena MCP should be used especially before:

- Adding a new service/module
- Changing endpoint behavior
- Changing generation flow
- Adding database models or migrations
- Adding background jobs
- Adding memory behavior
- Changing file handling
- Adding custom agents
- Refactoring shared code

The agent must not guess where things belong if Serena MCP can inspect the actual code structure.

If Serena MCP is unavailable, state that clearly and fall back to careful local search, but keep changes smaller.

---

## CustomAgent Requirement

When creating or using a CustomAgent for this project, it must follow the same clean architecture rules as the main integration.

The recommended CustomAgent role is:

```text
Name: DeepAgentsArchitectureAgent

Purpose:
Analyze, design, and implement the LangChain Deep Agents orchestration layer while preserving the existing presentation engine.

Primary tools:
- Serena MCP for codebase analysis
- Existing project tools and tests
- MCP tools exposed by the presentation engine, when needed

Core behavior:
- Analyze before editing.
- Use Serena MCP for every meaningful codebase analysis.
- Keep changes isolated.
- Preserve legacy behavior.
- Prefer async-safe implementation.
- Keep file and memory boundaries strict.
- Add tests for every new behavior.
- Report risks clearly.
```

A CustomAgent must always be compatible with:

- Existing presentation generation
- Existing API contracts
- Existing database/session lifecycle
- Existing async/background task style
- Existing file parsing and upload behavior
- Existing MCP server behavior
- Existing frontend expectations
- Existing export behavior

The CustomAgent must not create a parallel presentation engine.

The CustomAgent must not introduce a second architecture that competes with the current one.

The CustomAgent must extend the system through a clean orchestration layer.

---

## Deep Agents Module Shape

Prefer the following module shape or the closest equivalent that matches the existing project layout:

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

Responsibilities:

- `config.py`: environment/settings parsing
- `schemas.py`: Pydantic schemas for plans, evidence, quality reports, and run results
- `prompts.py`: supervisor and subagent prompts
- `backend.py`: Deep Agents state and memory backend configuration
- `permissions.py`: file permission policy
- `mcp.py`: MCP tool loading
- `tools.py`: small local utility tools
- `agent_factory.py`: Deep Agent construction
- `runner.py`: async orchestration entrypoint
- `jobs.py`: database run state and background worker lifecycle
- `memory.py`: memory seeding, validation, patching, and safety
- `auto_mode.py`: cron-safe auto mode entrypoints
- `errors.py`: custom exceptions

If the existing project uses a different directory convention, adapt to that convention while keeping this separation of responsibilities.

---

## Feature Flags

Use feature flags to protect the legacy path.

Recommended environment variables:

```bash
PRESENTATION_ORCHESTRATOR=legacy
DEEPAGENTS_ENABLED=false
DEEPAGENTS_MODEL_PROVIDER=openai
DEEPAGENTS_MODEL_NAME=gpt-4.1-mini
DEEPAGENTS_MEMORY_MODE=review
DEEPAGENTS_AUTO_MODE=false
DEEPAGENTS_MCP_URL=http://127.0.0.1:8001/mcp
DEEPAGENTS_MAX_RETRIES=2
DEEPAGENTS_MAX_QA_LOOPS=1
DEEPAGENTS_RUN_TIMEOUT_SECONDS=900
```

Supported orchestrator values:

```text
legacy
deepagents
```

Supported memory modes:

```text
off
review
auto
```

Legacy mode must remain the default.

---

## State Management Rules

State must be separated into three categories:

### 1. Request state

Short-lived request data.

Rules:

- Do not store large raw files here.
- Do not store secrets.
- Do not pass request-scoped database sessions into background jobs.

### 2. Run state

Persistent job/run status.

Rules:

- Store status, step, message, timestamps, input snapshot, output snapshot, and error snapshot.
- Input snapshots must contain sanitized metadata, not raw file bodies.
- Output snapshots must be JSON serializable.
- Failed jobs must be marked failed and must not stay stuck in running state.

### 3. Agent state

Deep Agents thread/workspace state.

Rules:

- Thread-scoped state can be temporary.
- Long-term memory must be explicit.
- Use `thread_id` consistently.
- Do not mix users in the same memory namespace.

---

## File Management Rules

Use clear virtual boundaries:

```text
/inputs/**      read-only user input
/workspace/**   temporary agent workspace
/outputs/**     generated plans, reports, patches
/memories/**    long-term memory only when allowed
```

Rules:

1. Never write to `/inputs`.
2. Never write to application source code through agent filesystem tools.
3. Never write to `.env`, secrets, config secrets, credentials, or key files.
4. Never store raw uploaded files in memory.
5. Sanitize all file metadata before passing it to the agent.
6. Use safe references for uploaded files.
7. Avoid prompt-injecting entire long documents.
8. Prefer summaries, chunks, and evidence references.

---

## Memory Rules

Memory must be safe and deliberate.

### `off`

- Do not write memory.
- Do not seed memory.
- Do not create memory patches.

### `review`

- Do not edit `/memories`.
- Write only a proposed patch under `/outputs/{presentation_id}/memory_patch.md`.

### `auto`

- May update `/memories`.
- Only save durable, reusable lessons.
- Validate memory updates before writing.
- Must be suitable for cron execution.

Allowed memory:

- User-stated presentation preferences
- Durable design preferences
- Reusable deck patterns
- Reusable failure lessons
- Language/tone/export preferences
- Template/layout lessons

Forbidden memory:

- Secrets
- API keys
- Credentials
- Raw uploaded documents
- Sensitive personal data
- One-off request details
- Unverified factual claims
- Large generated output dumps

---

## Async and Background Job Rules

All Deep Agents execution must be async.

Rules:

1. Use async runner functions.
2. Use `await agent.ainvoke(...)`.
3. Use timeouts.
4. Use fresh database sessions inside background jobs.
5. Close sessions reliably.
6. Mark failed jobs as failed.
7. Do not block the event loop with heavy sync work.
8. Cron jobs must support dry-run.
9. Cron jobs must be lock-protected to avoid duplicate execution.

---

## MCP Rules

The Deep Agents layer should use MCP tools exposed by the existing presentation engine.

Rules:

1. Load MCP tools asynchronously.
2. Fail clearly if MCP server is unavailable.
3. Fail clearly if no tools are returned.
4. Do not duplicate MCP tool behavior in the orchestrator.
5. Do not call export before planning and quality review pass.
6. Log tool names only at debug level.
7. Do not leak secrets in tool logs.

---

## Quality Rules

The goal is Gamma-like clean presentation quality.

Quality means:

- One main idea per slide
- Clear narrative flow
- Low-to-medium text density
- Strong title hierarchy
- Evidence-backed claims
- No hallucinated numbers
- Layout intent matches slide purpose
- Export result is verified
- Memory updates are safe

A bounded quality loop is required.

Rules:

1. Use a maximum QA loop count.
2. Never loop forever.
3. If quality remains poor, return partial instead of pretending success.
4. High-severity issues must be visible in the output.
5. Export must be verified before final success.

---

## Testing Rules

Add tests for every new behavior.

Minimum expected tests:

- schema validation
- backend factory
- filesystem permissions
- MCP unavailable behavior
- runner smoke tests with mocked agent
- job state lifecycle
- memory mode behavior
- deterministic layout fallback
- file input sanitization

Tests must not require:

- real LLM calls
- real API keys
- a running MCP server
- external network access

Mock external dependencies.

---

## Compatibility Rules

Every change must be compatible with the existing project.

Before editing, inspect the current style for:

- imports
- settings
- database sessions
- models
- migrations
- service naming
- endpoint response shapes
- error handling
- logging
- tests

Do not introduce a new pattern when an existing safe pattern exists.

When uncertain, prefer the smallest compatible change.

---

## Final Response Format for Coding Agents

After each task, report:

```text
Summary:
- What changed

Files changed:
- path/to/file

Validation:
- command run or reason not run

Compatibility:
- how legacy behavior was preserved

Risks:
- known limitations or follow-up work
```

Do not include secrets.

Do not include branch names.

Do not include repository remote details.
