# Deep Agents Integration

## Overview

The Deep Agents orchestration layer adds intelligent planning, evidence mapping, file-aware context, quality review, memory, and auto-mode capabilities on top of the existing presentation generation engine.

The system preserves the legacy presentation flow as the default. Deep Agents mode must be explicitly enabled via feature flags.

## Architecture

```
User Request
    |
    v
Orchestrator (legacy vs deepagents)
    |
    +-- legacy (default) --> existing presentation engine
    |
    +-- deepagents --> create_deck_agent
                          |
                          +-- Supervisor Agent (orchestrates subagents)
                          |     +-- Research Planner
                          |     +-- Slide Architect
                          |     +-- Quality Reviewer
                          |
                          +-- MCP Tools (presentation engine tools)
                          +-- Backend (state + memory store)
                          +-- Permissions (filesystem access policy)
                          +-- Memory seeds (read-only in review mode)
                          |
                          v
                     DeepAgentRunResult
```

All orchestration code is isolated under `services/deepagents/` in the FastAPI server.

## Feature Flags

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `PRESENTATION_ORCHESTRATOR` | `legacy` | `legacy` or `deepagents` |
| `DEEPAGENTS_ENABLED` | `false` | Additional toggle for Deep Agents mode |
| `DEEPAGENTS_MODEL_PROVIDER` | `openai` | LLM provider for the agent |
| `DEEPAGENTS_MODEL_NAME` | `gpt-4.1-mini` | LLM model name |
| `DEEPAGENTS_MEMORY_MODE` | `review` | `off`, `review`, or `auto` |
| `DEEPAGENTS_AUTO_MODE` | `false` | Enable cron-safe auto mode |
| `DEEPAGENTS_MCP_URL` | `http://127.0.0.1:8001/mcp` | MCP server URL |
| `DEEPAGENTS_MAX_RETRIES` | `2` | Maximum retry count |
| `DEEPAGENTS_MAX_QA_LOOPS` | `1` | Maximum quality review loops |
| `DEEPAGENTS_RUN_TIMEOUT_SECONDS` | `900` | Timeout per run |

Legacy mode remains the default. The orchestrator checks `PRESENTATION_ORCHESTRATOR` first and falls back to `DEEPAGENTS_ENABLED` for backward compatibility.

## State Management

State is separated into three categories:

### 1. Request State
Short-lived request data. Sanitized before storing. Stored as `input_snapshot` on run records. File bodies are excluded from snapshots.

### 2. Run State
Persistent job status in the `deepagent_presentation_runs` table. Stores status, step, message, timestamps, input snapshot (metadata only), output snapshot, and error snapshot.

### 3. Agent State
Thread-scoped state managed by the Deep Agents backend. Long-term memory is stored under `/memories/` and backed by the `StoreBackend`. State is namespaced by user ID.

## File Management

Virtual boundary rules enforced by the permission policy:

| Path | Read | Write |
|------|------|-------|
| `/inputs/**` | Allowed | Denied |
| `/workspace/**` | Allowed | Allowed |
| `/outputs/**` | Allowed | Allowed |
| `/config/**` | Allowed | Denied |
| `/memories/**` (auto) | Allowed | Allowed |
| `/memories/**` (review) | Allowed | Denied |
| `/memories/**` (off) | Denied | Denied |

### File Input Strategy (Task 17)

When the agent receives file inputs, they are sanitized before reaching the agent:

- File metadata is extracted: file_id, filename, mime_type, summary, safe_ref
- Raw file content is not passed to the agent
- Path traversal is checked and rejected
- Missing files produce readable errors
- Evidence items can reference files via `source_ref` and `safe_ref`

## Memory Modes

### `off`
- No memory reads or writes
- No memory seed files created
- Agent cannot access `/memories/` at all

### `review` (recommended default)
- Memory reads allowed
- Memory writes denied
- Agent writes proposed memory patches to `/outputs/{presentation_id}/memory_patch.md`
- No direct `/memories/` edits

### `auto`
- Full memory reads and writes
- Only for cron/auto-mode execution
- Memory updates are validated before saving
- Validation rejects: secrets, API keys, raw documents, personal data, uncertain claims

## Memory Write Safety (Task 18)

Memory patches are validated by `validate_memory_patch()`:

**Allowed memory:**
- User-stated presentation preferences
- Durable deck style preferences
- Successful reusable design patterns
- Failure lessons and fixes
- Language, tone, or export preferences
- Template/layout lessons

**Rejected memory:**
- API keys or secrets
- Sensitive personal data (emails, SSNs)
- One-off request details
- Raw uploaded document contents
- Unverified factual claims
- Temporary scratch reasoning
- Large generated outputs (>200KB)

## Auto Mode and Cron Usage

Auto mode provides three CLI commands:

```bash
# Generate a presentation from a saved request JSON
python -m services.deepagents.auto_mode generate \
    --request-json /path/to/request.json \
    --memory-mode auto \
    --dry-run

# Consolidate memory from recent runs
python -m services.deepagents.auto_mode memory_consolidate \
    --user-id user-abc \
    --memory-mode auto \
    --dry-run

# Re-check quality of a previous run
python -m services.deepagents.auto_mode quality_recheck \
    --run-id <uuid> \
    --dry-run
```

All auto commands support `--dry-run` to simulate without writing state. Lock-protection prevents duplicate cron execution.

### Cron dry-run behavior
- Dry-run does not write memory, create runs, or modify state
- Returns a status of `dry_run` with a simulation message

## MCP Dependency

Deep Agents mode requires a running MCP server (default: `http://127.0.0.1:8001/mcp`). If unavailable:

- The `run_deepagents_presentation_generation` returns a failed `DeepAgentRunResult` with a readable error message
- The error is logged
- The agent is not created

The MCP connection is established inside `load_presentation_mcp_tools()`. Tools are loaded asynchronously. If zero tools are returned, an `MCPUnavailableError` is raised.

## Async Lifecycle

1. `create_deepagent_run()` — creates a pending run record in the database
2. `mark_run_started()` — marks the run as running
3. `run_deepagents_presentation_generation()` — creates the agent, builds the user message, invokes the agent
4. Quality review loop — bounded by `deepagents_max_qa_loops`
5. `mark_run_completed()` or `mark_run_failed()` — finalizes the run

All execution is async. Background jobs use fresh database sessions (not request-scoped). Step callbacks also use fresh sessions inside background workers.

## Failure Handling

| Failure Mode | Behavior |
|-------------|----------|
| MCP unavailable | Returns `DeepAgentRunResult(status="failed")` with error message |
| Agent timeout (asyncio.TimeoutError) | Returns `DeepAgentRunResult(status="failed")` with `RunTimeoutError` |
| Agent returns no output | Returns `DeepAgentRunResult(status="failed")` |
| Quality review loop times out | Loop breaks, warning added, result returned as partial |
| High-severity quality issues | Status marked as `partial` if score < 80 |
| Background job exception | Run marked as failed with error snapshot |

## Deterministic Layout Fallback (Task 16)

The `choose_deterministic_layout()` function provides repeatable layout selection:

1. If layout index is valid, use it
2. If invalid, match by `preferred_layout_tags`
3. If no tag match, match by slide `purpose`
4. If no purpose match, match by `content_density`
5. Otherwise, return index 0

Same inputs always produce the same output. No random fallback is used in Deep Agents mode.

## Local Development

1. Clone the repository
2. Set up the Python environment using the provided `pyproject.toml`
3. Set `PRESENTATION_ORCHESTRATOR=deepagents` to enable Deep Agents mode
4. Ensure the MCP server is running (default: port 8001)
5. Set feature flags as needed (see Feature Flags table)

Testing:

```bash
cd servers/fastapi
pytest tests/deepagents/ -v
```

Tests mock all external dependencies. No real LLM calls or MCP server needed.

## Production Notes

- Set `DEEPAGENTS_MEMORY_MODE=review` for safety (recommended default)
- Never set `DEEPAGENTS_AUTO_MODE=true` without lock protection
- Monitor MCP server availability
- Review memory patches under `/outputs/` before promoting to `/memories/`
- Set realistic timeout values based on model and complexity
- Keep `DEEPAGENTS_MAX_QA_LOOPS` low (1-2) to avoid runaway loops

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Agent fails with MCP error | MCP server not running | Start MCP server at `DEEPAGENTS_MCP_URL` |
| Agent returns empty result | Invalid thread_id | Ensure non-empty `thread_id` is provided |
| Run stuck in "running" | Timeout or crash | Check logs, mark as failed manually |
| Memory writes fail silently | Memory mode is `off` or `review` | Switch to `auto` mode for writes |
| Quality review loops forever | `deepagents_max_qa_loops` too high | Set to 1 or 2 |
