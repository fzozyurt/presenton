# TASK 09 — Create the async Deep Agents runner

## Goal

Create a single async orchestration entrypoint that can be used by sync endpoints, async endpoints, background jobs, and cron.

## File

`services/deepagents/runner.py`

## Implement

```python
async def run_deepagents_presentation_generation(
    *,
    request,
    presentation_id: str,
    thread_id: str,
    user_id: str | None,
    auto_mode: bool,
    memory_mode: str,
    export_cookie_header: str | None = None,
) -> DeepAgentRunResult:
    ...
```

## Required behavior

1. Require `thread_id`.
2. Create the agent with `await create_deck_agent(settings)`.
3. Build a concise user message from the request.
4. Use `await agent.ainvoke(...)`.
5. Pass thread metadata through config.
6. Add timeout protection.
7. Normalize output into `DeepAgentRunResult`.
8. Return failed result instead of leaking internal exceptions.
9. Do not use a request-scoped database session.
10. Do not perform blocking I/O.

## User message template

```text
Create a presentation using the existing presentation engine.

presentation_id: {presentation_id}
thread_id: {thread_id}
auto_mode: {auto_mode}
memory_mode: {memory_mode}

Request:
- content: {content}
- number_of_slides: {n_slides}
- language: {language}
- tone: {tone}
- verbosity: {verbosity}
- instructions: {instructions}
- template: {template}
- export_as: {export_as}
- web_search: {web_search}
- files: {files}

Important:
1. Create DeckPlan before generating/exporting.
2. Use available presentation-engine tools for actual generation and export.
3. Validate the result before final response.
4. Save generated planning/report artifacts under /outputs/{presentation_id}/.
5. If memory_mode is review, write memory_patch.md under /outputs/{presentation_id}/ and do not edit /memories.
6. If memory_mode is auto, update /memories only with durable reusable lessons.
```

## Config template

```python
config = {
    "configurable": {
        "thread_id": thread_id,
    },
    "metadata": {
        "presentation_id": presentation_id,
        "user_id": user_id or "anonymous",
        "auto_mode": auto_mode,
        "memory_mode": memory_mode,
        "orchestrator": "deepagents",
    },
}
```

## Acceptance criteria

- The runner is fully async.
- Missing `thread_id` fails fast.
- MCP/agent failures return `DeepAgentRunResult(status="failed")`.
- Successful execution returns `DeepAgentRunResult(status="completed")` or `partial`.
- Output is JSON serializable.
