# TASK 16 — Add deterministic layout fallback for Deep Agents mode

## Goal

Avoid random layout fallback in Deep Agents mode because it lowers repeatability and quality.

## Required behavior

Do not change legacy behavior unless explicitly necessary.

For Deep Agents mode:

1. If layout index is valid, use it.
2. If layout index is invalid:
   - choose a layout matching `preferred_layout_tags`
   - otherwise choose by slide `purpose`
   - otherwise choose by `content_density`
   - otherwise choose the first safe readable layout
3. Do not use random fallback.
4. Same input should produce same fallback layout.

## Suggested helper

```python
def choose_deterministic_layout(
    *,
    available_layouts: list,
    slide_plan,
    requested_layout_index: int | None,
):
    ...
```

## Acceptance criteria

- Legacy mode remains unchanged.
- Deep Agents mode does not use random fallback.
- Invalid layout index is handled safely.
- Unit tests cover at least:
  - valid index
  - invalid index with matching tags
  - invalid index with no tags
  - empty layout list
