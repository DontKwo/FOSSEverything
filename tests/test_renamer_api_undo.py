from __future__ import annotations

from pathlib import Path

from app.web.api import WebApi


def _steps() -> list[dict[str, object]]:
    # Two-rule stack: replace text then number sequence.
    return [
        {"type": "replace_text", "enabled": True, "find_text": "draft", "replace_with": "final", "match_case": False, "scope": "all"},
        {"type": "number_sequence", "enabled": True, "mode": "suffix", "start_at": 1, "increment": 1, "padding": 2, "separator": "_"},
    ]


def test_renamer_execute_then_undo_restores_names(tmp_path: Path) -> None:
    # One undo call reverses the whole last batch rename.
    api = WebApi()
    originals = []
    for name in ("draft_a.txt", "draft_b.txt"):
        path = tmp_path / name
        path.write_text(name, encoding="utf-8")
        originals.append(str(path))

    res = api.renamer_execute({"file_paths": originals, "steps": _steps()})
    assert res["ok"] is True
    assert res["renamed_count"] == 2
    assert res["undo_available"] is True
    assert (tmp_path / "final_a_01.txt").exists()
    assert (tmp_path / "final_b_02.txt").exists()

    undone = api.renamer_undo({})
    assert undone["ok"] is True
    assert undone["restored_count"] == 2
    assert (tmp_path / "draft_a.txt").exists()
    assert (tmp_path / "draft_b.txt").exists()


def test_renamer_preview_flags_collisions_without_auto_resolve(tmp_path: Path) -> None:
    # Duplicate destinations are flagged when auto-numbering is off.
    api = WebApi()
    paths = []
    for name in ("one.txt", "two.txt"):
        path = tmp_path / name
        path.write_text(name, encoding="utf-8")
        paths.append(str(path))
    steps = [{"type": "replace_text", "enabled": True, "find_text": "one", "replace_with": "two", "scope": "all"}]
    flagged = api.renamer_preview({"file_paths": paths, "steps": steps, "auto_resolve_conflicts": False})
    assert flagged["has_conflicts"] is True
    resolved = api.renamer_preview({"file_paths": paths, "steps": steps, "auto_resolve_conflicts": True})
    assert resolved["has_conflicts"] is False
