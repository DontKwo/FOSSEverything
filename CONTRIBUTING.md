# Contributing to FOSSEverything

Thanks for considering a contribution. This project is local-first, offline-by-default,
and free software (AGPL-3.0-or-later, see [LICENSE](LICENSE) and [NOTICES.md](NOTICES.md)) --
please keep those properties intact in anything you submit.

## Setting up a dev environment

```bash
git clone https://github.com/your-username/fosseverything.git
cd fosseverything
uv sync
uv run python main.py
```

`uv sync` installs the exact locked dependency versions from `uv.lock`. If you add a new
dependency, use `uv add <package>` rather than editing `pyproject.toml` by hand, so the
lockfile stays consistent.

## Running tests

```bash
uv run pytest
```

Tests live in `tests/`, mirroring `app/features/<feature>/ops.py` module names
(`test_<feature>_ops.py`). Domain logic in `*_ops.py` modules is written to be testable
without a Qt event loop -- prefer testing at that layer over driving the UI. If a test does
need a real `QApplication`, run it headlessly with `QT_QPA_PLATFORM=offscreen`.

## Architecture conventions

- Each workspace under `app/features/<name>/` splits into `ops.py` (headless domain logic,
  no PyQt imports) and `tab.py` (the Qt widget that wires `ops.py` functions to buttons/menus).
  Keep that split -- it's what makes `ops.py` unit-testable and reusable outside the GUI.
- New workspaces register with the shared workspace/tool registry (`app/core/tool_registry.py`)
  rather than adding one-off hardcoded checks in the shell, so Home, search, and file routing
  pick them up automatically.
- A missing optional backend (Ghostscript, Calibre, a local Java runtime for LanguageTool, a
  local rembg model, etc.) should disable only the capability that needs it, never crash the
  whole app. Follow the existing `*_backend_available()` gating pattern used throughout.
- Every button/box-type widget should have a tooltip via `get_tooltip_for(label)`
  (`app/core/tooltips.py`) -- it's safe to call with any label even before the label is
  registered in the tooltip dictionary.
- `FUNCTIONALITY_AND_FUTURE_WORK.md` is the product map: it should never claim a capability
  exists before it's actually implemented and wired into the UI.

## Code style and required checks

This repo uses a project-specific static linter (checks for things like unwrapped exceptions,
hardcoded paths, missing tooltips, and dialog text that isn't selectable) in addition to normal
Python style. Before opening a PR:

1. Run `python -m py_compile <changed files>` to catch syntax errors.
2. Fix anything the linter your editor/CI surfaces for the files you touched.
3. Run `uv run pytest` and make sure nothing you touched regresses.
4. Keep changes scoped to what the PR describes -- avoid unrelated refactors in the same PR.

## Licensing of contributions

By submitting a pull request, you agree your contribution is licensed under the same
AGPL-3.0-or-later terms as the rest of the project (see [LICENSE](LICENSE)).
