# Failure Lessons

## Known Risks

- Too much text reduces perceived quality.
- Random layout fallback can lower repeatability and quality.
- Unsupported or missing evidence should be marked instead of invented.
- Export must be verified before returning success.
- Raw uploaded files must not be written into memory.

## Fix Patterns

- If a slide is overloaded, split or compress it.
- If evidence is missing, lower confidence and avoid precise claims.
- If layout is uncertain, choose the simplest readable layout.
- If export fails, return partial or failed status with a clear error.
- If memory update is unsafe, reject it and write a warning.
