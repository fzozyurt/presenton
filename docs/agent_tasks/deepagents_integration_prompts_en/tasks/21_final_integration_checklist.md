# TASK 21 — Final integration checklist

## Goal

Run this final checklist before merging or deploying the Deep Agents integration.

## Checklist

- [ ] Legacy generation still works.
- [ ] `PRESENTATION_ORCHESTRATOR=legacy` is the default.
- [ ] `PRESENTATION_ORCHESTRATOR=deepagents` enables the new orchestrator.
- [ ] Deep Agents runner uses `ainvoke`.
- [ ] MCP unavailable case produces a readable error.
- [ ] Background job does not receive request-scoped database session objects.
- [ ] Deep Agent run status polling works.
- [ ] Memory mode `off` works.
- [ ] Memory mode `review` works.
- [ ] Memory mode `auto` works.
- [ ] Cron dry-run does not write memory.
- [ ] User file inputs are read-only.
- [ ] Agent writes are limited to approved workspace, output, and memory paths.
- [ ] Quality review loop has a max limit.
- [ ] Output is JSON serializable.
- [ ] Export path is verified before success.
- [ ] Tests pass.
- [ ] Documentation is complete.

## Required final report

After implementation, provide this report:

1. Changed files
2. New files
3. New environment variables
4. New endpoints
5. How legacy behavior is preserved
6. Where transient state is stored
7. Where long-term memory is stored
8. How cron can run auto mode
9. Which tests were added
10. Known risks and follow-up work

## Acceptance criteria

- The final report is complete.
- No branch or repository metadata is included.
- No secrets are included.
