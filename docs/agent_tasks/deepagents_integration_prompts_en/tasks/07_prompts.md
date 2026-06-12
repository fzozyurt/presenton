# TASK 07 — Add supervisor and subagent prompts

## Goal

Add short, strict, English system prompts for the supervisor and subagents. The prompts must be suitable for a modest coding or reasoning model.

## Files

- `services/deepagents/prompts.py`
- Also copy prompt text from `agent_prompts/` if this package is being used as task input.

## Required prompt constants

Create these constants:

```python
SUPERVISOR_SYSTEM_PROMPT: str
RESEARCH_PLANNER_PROMPT: str
SLIDE_ARCHITECT_PROMPT: str
QUALITY_REVIEWER_PROMPT: str
```

## Rules

- Do not mention Agno.
- Do not mention branch names.
- Do not mention repository names.
- Be explicit about file safety.
- Be explicit about memory mode behavior.
- Require structured plan before generation/export.
- Require quality review before final success.
- Require finite retry loops.

## Acceptance criteria

- Prompt constants import correctly.
- Prompt text is English.
- Prompt text includes state, file, memory, and quality rules.
- Prompt text does not include git or branch workflow instructions.
