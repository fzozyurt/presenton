# Environment Example

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

## Recommended defaults

Use legacy mode by default.

Use memory mode `review` by default.

Enable `auto` mode only for controlled cron or internal automation.
