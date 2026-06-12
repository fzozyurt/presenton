# TASK 01 — Add Deep Agents dependencies and feature flags

## Goal

Add LangChain Deep Agents dependencies to the backend in a controlled way without changing the legacy presentation generation behavior.

## Files to inspect or update

- Backend dependency file
- Backend lock file, if present
- Environment example file, if present
- Settings/config module, if present

## Instructions for the coding agent

Add the following dependencies, using the project's existing dependency management style:

```toml
"deepagents>=0.6.8",
"langchain>=1.0.0",
"langchain-core>=1.0.0",
"langchain-mcp-adapters>=0.1.0",
"langgraph>=1.0.0",
"langgraph-checkpoint>=3.0.0",
```

If exact versions conflict with the current dependency graph, choose the closest compatible versions and document the reason.

Add these environment variables to the environment example and settings layer:

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

Supported values:

```text
PRESENTATION_ORCHESTRATOR:
- legacy
- deepagents

DEEPAGENTS_MEMORY_MODE:
- off
- review
- auto
```

Default behavior must remain legacy.

Do not make Deep Agents imports run during application startup unless Deep Agents mode is enabled or the relevant module is imported explicitly.

## Acceptance criteria

- The backend starts in legacy mode.
- Existing presentation generation still works in legacy mode.
- The application can read all new environment variables.
- Deep Agents dependencies install successfully.
- No Deep Agents code executes when `PRESENTATION_ORCHESTRATOR=legacy`.
