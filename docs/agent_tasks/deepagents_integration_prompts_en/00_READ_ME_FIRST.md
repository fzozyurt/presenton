# LangChain Deep Agents Integration Prompt Pack

This package contains English, copy-paste-ready task prompts for integrating LangChain Deep Agents into an existing presentation generation backend.

## Scope

Use LangChain Deep Agents only.

Do not introduce Agno.

Do not rewrite the existing presentation generation, template, or export engine. Add a clean orchestration layer on top of it.

## Critical rules

1. Keep the legacy generation path working.
2. Add the Deep Agents path behind feature flags.
3. All Deep Agents execution must be asynchronous.
4. Background and cron jobs must not reuse request-scoped database sessions.
5. User-uploaded files must be treated as read-only.
6. Agent workspace files must be isolated from the application source code.
7. Long-term memory must only be written under explicit memory paths.
8. Default memory mode should be `review`, not `auto`.
9. Auto mode must be safe for future cron execution.
10. Use schemas and small deterministic steps because the coding model may be modest.

## Recommended implementation order

Use the files in `tasks/` in numeric order.

Suggested split:

- First implementation batch: tasks 01-08
- Second implementation batch: tasks 09-15
- Third hardening batch: tasks 16-21

## Included folders

- `tasks/`: coding-agent task prompts.
- `agent_prompts/`: supervisor and subagent system prompts.
- `memory_seeds/`: initial long-term memory seed files.
- `checklists/`: final review checklist.

## No branch or repository information

This package intentionally does not include branch names, repository names, remote URLs, or git workflow instructions.
