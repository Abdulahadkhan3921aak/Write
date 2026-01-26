# GUI: Unsaved Tabs + Lightweight Linting

## Goals

- Prevent data loss by prompting before closing dirty tabs or quitting.
- Offer fast, low-noise linting and keyword/grammar hints without impacting typing latency.
- Keep implementation minimal and PySide6-friendly so it can ship quickly.

## Unsaved-Tab Confirmation

- Track per-tab dirty state (document modified vs. last save/load).
- When closing a tab or quitting the app:
  - If clean: close immediately.
  - If dirty: modal prompt with **Save / Don't Save / Cancel**.
  - Save uses existing path when present; otherwise opens a save dialog.
  - Cancel aborts the close.
- Tab label prefix `*` indicates unsaved changes.
- Build-path scratch artifacts cleaned only after the user confirms closing.

## Lightweight Linting / Suggestions

- Triggered on text edits with a short debounce (~200 ms); skipped on large buffers (>8 KB) to stay fast.
- Heuristic, zero-parse checks (regex/counting only) to avoid slowing typing:
  - Function block balance: `function`/`func` count vs. `end_function`/`end_func`.
  - `arguments` lines missing `:`.
  - `call` lines missing `arguments:`.
  - Trailing whitespace lines.
  - List declarations missing an explicit `size` keyword.
- Results surface in a dedicated **Lint** tab and highlight matching lines inline in the editor; empty state shows "No lint hints".
- Hints reset per edit; kept separate from compiler diagnostics to avoid conflation.

## Next Steps / Extensions

- Added Ctrl+S (Save) and Ctrl+Shift+S (Save As) bindings; consider adding "Save All".
- Add inline gutter markers for lint hints (optional) and richer hints using the parser in a background thread if performance remains good.
- Persist last-lint summary per tab so switching tabs restores hints without recomputing.
