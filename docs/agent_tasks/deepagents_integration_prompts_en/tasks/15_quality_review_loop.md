# TASK 15 — Add quality review loop

## Goal

Improve output quality using a bounded quality review loop before final success.

## Files

- `services/deepagents/runner.py`
- `services/deepagents/prompts.py`
- `services/deepagents/schemas.py`

## Required flow

1. Agent creates `DeckPlan`.
2. Quality reviewer evaluates the plan.
3. If score is below 80:
   - request one revision, unless max QA loops is 0.
4. If any high severity issue exists:
   - fix before export if possible.
5. Export only after plan quality passes or the max loop limit is reached.
6. After export, perform final checks:
   - presentation id exists
   - edit path exists if expected
   - export path exists if expected
   - slide count approximately matches requested count
7. Return `DeckQualityReport`.

## Loop rules

- Use `DEEPAGENTS_MAX_QA_LOOPS`.
- Never loop forever.
- Keep reviewer output short.
- Store quality report in output snapshot.
- If quality remains poor, return `partial` instead of pretending success.

## Acceptance criteria

- Quality score is present in run output.
- High severity issues are visible.
- Max loop is respected.
- Partial result is possible.
- Export success is verified.
