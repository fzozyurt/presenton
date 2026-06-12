# TASK 20 — Add Deep Agents integration documentation

## Goal

Document how the new orchestration layer works.

## File

Create:

```text
docs/deepagents-integration.md
```

If the project has a different docs location, use the closest equivalent.

## Required sections

1. Overview
2. Architecture
3. Feature flags
4. State management
5. File management
6. Memory modes
7. Auto mode and cron usage
8. MCP dependency
9. Async lifecycle
10. Failure handling
11. Local development
12. Production notes
13. Troubleshooting

## Must include

- Legacy mode remains the default.
- Deep Agents mode requires the MCP server.
- Background workers must not use request-scoped database sessions.
- Memory mode `review` is the recommended default.
- Auto mode is designed for future cron execution.
- Preview async subagents are not used in the first implementation.
- Minimum-model reliability depends on schemas, bounded loops, and strict prompts.

## Acceptance criteria

- A new developer can enable Deep Agents mode locally.
- The memory modes are clear.
- The cron dry-run behavior is clear.
- Failure recovery is explained.
- No branch or repository metadata is included.
