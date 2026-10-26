import importlib
import inspect
import json
import re
from pathlib import Path
from typing import Any

import pytest


def calc_load_json(filename: str) -> Any:
    # Load JSON file from tests/parity directory.
    path = Path(__file__).parent / "parity" / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_parity_ops_kept() -> None:
    # Assert all ops functions and parameter names on main are preserved.
    ops_inv = calc_load_json("ops_inventory.json")
    mismatches: list[str] = []

    for mod_path, funcs in ops_inv.items():
        mod_name = mod_path.replace("/", ".").removesuffix(".py")
        try:
            mod = importlib.import_module(mod_name)
        except Exception as exc:
            mismatches.append(f"Import error for {mod_name}: {exc}")
            continue

        for func_name, expected_params in funcs.items():
            if "." in func_name:
                cls_name, m_name = func_name.split(".", 1)
                target_cls = getattr(mod, cls_name, None)
                if not target_cls:
                    mismatches.append(f"{mod_name}: class {cls_name} missing")
                    continue
                fn = getattr(target_cls, m_name, None)
                if not fn:
                    mismatches.append(f"{mod_name}: method {func_name} missing")
                    continue
                if isinstance(fn, property):
                    fn = fn.fget
                sig = inspect.signature(fn)
                params = [p for p in sig.parameters.keys() if p not in ("self", "cls")]
                exp = [p for p in expected_params if p not in ("self", "cls")]
                if params != exp:
                    mismatches.append(f"{mod_name}:{func_name} params {params} != expected {exp}")
            else:
                fn = getattr(mod, func_name, None)
                if not fn:
                    mismatches.append(f"{mod_name}: function {func_name} missing")
                    continue
                sig = inspect.signature(fn)
                params = list(sig.parameters.keys())
                if params != expected_params:
                    mismatches.append(f"{mod_name}:{func_name} params {params} != expected {expected_params}")

    assert not mismatches, f"Ops mismatches found ({len(mismatches)}):\n" + "\n".join(mismatches[:30])


def test_parity_gui_coverage() -> None:
    # Assert every Qt tab call is referenced by WebApi or allowlisted.
    tab_calls = calc_load_json("tab_calls.json")
    allowlist = calc_load_json("allowlist.json")

    api_texts: list[str] = []
    api_dir = Path("app/web/api")
    if api_dir.exists():
        for p in api_dir.rglob("*.py"):
            api_texts.append(p.read_text(encoding="utf-8", errors="replace"))
    old_api = Path("app/web/api.py")
    if old_api.exists():
        api_texts.append(old_api.read_text(encoding="utf-8", errors="replace"))

    combined_api = "\n".join(api_texts)
    missing: list[str] = []

    for tab_file, calls in tab_calls.items():
        for call_item in calls:
            if call_item in allowlist:
                continue
            name = call_item.split(":")[-1]
            pattern = r"\b" + re.escape(name) + r"\b"
            if not re.search(pattern, combined_api):
                missing.append(f"{tab_file} -> {call_item}")

    assert not missing, f"Uncovered GUI calls found ({len(missing)}):\n" + "\n".join(missing[:30])
