# Archived UI tests

These files reference UI features that were removed or rewritten in the
current generation of `ui.py` (first-run intro/tour system, voice intro
caching, graphics auto-detection, detached panels). They fail on import
because the symbols they patch no longer exist.

- `test_ui_regressions.py` — full-stack regression tests for the old UI
- `qa_ui_probe.py` — accessibility/render probe for the old UI

They are kept for reference and are intentionally excluded from test
discovery (they live in an `_archive/` folder). Re-introduce them only
after the current UI re-gains the tested features.
