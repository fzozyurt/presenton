# Memory Update Instruction

Use this instruction when the agent needs to handle long-term memory.

## Memory mode: off

Do not write memory.
Do not create memory seed files.
Do not create memory patches.

## Memory mode: review

Do not edit files under `/memories`.

Instead, create:

```text
/outputs/{presentation_id}/memory_patch.md
```

The patch should contain only safe, durable, reusable lessons.

## Memory mode: auto

You may update files under `/memories`, but only with validated durable information.

Allowed memory:

- user-stated presentation preferences
- durable design preferences
- reusable successful deck patterns
- reusable failure lessons
- language, tone, export, or layout preferences

Forbidden memory:

- secrets
- API keys
- raw uploaded documents
- sensitive personal data
- one-off request details
- uncertain factual claims
- large generated output dumps
