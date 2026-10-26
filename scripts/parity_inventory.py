import ast
import json
import re
import subprocess
from pathlib import Path


def calc_norm_label(text: str) -> str:
    # Normalize label string for comparison.
    t = text.replace("&&", "__AMP__")
    t = t.replace("&", "")
    t = t.replace("__AMP__", "&")
    t = t.lower()
    t = re.sub(r"\s+", " ", t).strip()
    while t.endswith("...") or t.endswith(":"):
        if t.endswith("..."):
            t = t[:-3].strip()
        elif t.endswith(":"):
            t = t[:-1].strip()
    return t


def calc_git_file(path: str) -> str:
    # Read file contents from main branch.
    cmd = ["git", "show", f"main:{path}"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    return proc.stdout


def calc_git_file_list() -> list[str]:
    # List all tracked files on main branch.
    cmd = ["git", "ls-tree", "-r", "main", "--name-only"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def calc_ops_inventory(all_files: list[str]) -> dict[str, dict[str, list[str]]]:
    # Extract public functions and methods from backend ops modules.
    target_files: list[str] = []
    for f in all_files:
        if f.startswith("app/features/") and f.endswith(".py"):
            parts = f.split("/")
            if len(parts) == 4 and parts[3] not in ("tab.py", "viewport.py", "__init__.py"):
                target_files.append(f)
        elif f.startswith("app/core/") and f.endswith(".py"):
            if f not in (
                "app/core/customizable_toolbar.py",
                "app/core/search_palette.py",
                "app/core/spinbox.py",
                "app/core/__init__.py",
            ):
                target_files.append(f)
        elif f == "app/system/shell_integration.py":
            target_files.append(f)

    target_files.sort()
    inventory: dict[str, dict[str, list[str]]] = {}
    for path in target_files:
        code = calc_git_file(path)
        tree = ast.parse(code)
        funcs: dict[str, list[str]] = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    param_names = [a.arg for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs]
                    funcs[node.name] = param_names
            elif isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not sub.name.startswith("_"):
                            param_names = [a.arg for a in sub.args.posonlyargs + sub.args.args + sub.args.kwonlyargs]
                            funcs[f"{node.name}.{sub.name}"] = param_names
        inventory[path] = funcs
    return inventory


def calc_tab_calls(all_files: list[str]) -> dict[str, list[str]]:
    # Extract imported functions and method calls used by Qt tabs.
    tab_files: list[str] = []
    for f in all_files:
        if f.endswith("/tab.py") or (
            f.startswith("app/ui/") and f.endswith(".py") and not f.endswith("__init__.py")
        ):
            tab_files.append(f)

    tab_files.sort()
    tab_calls: dict[str, list[str]] = {}
    for path in tab_files:
        code = calc_git_file(path)
        tree = ast.parse(code)
        alias_map: dict[str, tuple[str, str | None]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith(("app.features", "app.core", "app.system")):
                    for a in node.names:
                        local_name = a.asname or a.name
                        alias_map[local_name] = (node.module, a.name)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.startswith(("app.features", "app.core", "app.system")):
                        local_name = a.asname or a.name
                        alias_map[local_name] = (a.name, None)

        calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id in alias_map:
                    mod, orig = alias_map[node.value.id]
                    if orig == "ops":
                        calls.add(f"{mod}.ops:{node.attr}")
                    elif orig is None:
                        calls.add(f"{mod}:{node.attr}")
                    else:
                        calls.add(f"{mod}.{orig}:{node.attr}")
            elif isinstance(node, ast.Name) and node.id in alias_map:
                mod, orig = alias_map[node.id]
                if orig and orig != "ops":
                    calls.add(f"{mod}:{orig}")

        tab_calls[path] = sorted(calls)
    return tab_calls


def calc_qt_inventory(all_files: list[str]) -> dict[str, dict[str, list[str]]]:
    # Extract UI labels, placeholders, tooltips, and shortcuts from Qt files.
    tab_files: list[str] = []
    for f in all_files:
        if f.endswith("/tab.py") or (
            f.startswith("app/ui/") and f.endswith(".py") and not f.endswith("__init__.py")
        ):
            tab_files.append(f)

    tab_files.sort()
    inventory: dict[str, dict[str, list[str]]] = {}
    str_lit = r'["\']([^"\']+)["\']'

    for path in tab_files:
        code = calc_git_file(path)
        btns = [calc_norm_label(s) for s in re.findall(r"QPushButton\(\s*" + str_lit, code)]
        checks = [calc_norm_label(s) for s in re.findall(r"QCheckBox\(\s*" + str_lit, code)]
        radios = [calc_norm_label(s) for s in re.findall(r"QRadioButton\(\s*" + str_lit, code)]
        groups = [calc_norm_label(s) for s in re.findall(r"QGroupBox\(\s*" + str_lit, code)]
        groups.extend([calc_norm_label(s) for s in re.findall(r"\.setTitle\(\s*" + str_lit, code)])
        tabs = [calc_norm_label(s) for s in re.findall(r"addTab\([^,]+,\s*" + str_lit, code)]

        combos = [calc_norm_label(s) for s in re.findall(r"addItem\(\s*" + str_lit, code)]
        for items in re.findall(r"addItems\(\s*\[(.*?)\]", code, re.DOTALL):
            combos.extend([calc_norm_label(s) for s in re.findall(str_lit, items)])

        placeholders = [calc_norm_label(s) for s in re.findall(r"setPlaceholderText\(\s*" + str_lit, code)]
        tooltips = [calc_norm_label(s) for s in re.findall(r"setToolTip\(\s*" + str_lit, code)]
        raw_labels = re.findall(r"QLabel\(\s*" + str_lit, code)
        labels = [calc_norm_label(s) for s in raw_labels if len(s) >= 4]

        shortcuts_raw = re.findall(r"QKeySequence\(\s*" + str_lit, code)
        shortcuts_raw.extend(re.findall(r"setShortcut\(\s*" + str_lit, code))
        shortcuts = sorted(set(shortcuts_raw))

        inventory[path] = {
            "buttons": sorted(set(btns)),
            "checks": sorted(set(checks)),
            "radios": sorted(set(radios)),
            "groups": sorted(set(groups)),
            "tabs": sorted(set(tabs)),
            "combo_items": sorted(set(combos)),
            "placeholders": sorted(set(placeholders)),
            "tooltips": sorted(set(tooltips)),
            "labels": sorted(set(labels)),
            "shortcuts": shortcuts,
        }
    return inventory


def calc_doc_features() -> dict[str, dict[str, str]]:
    # Parse feature items from FUNCTIONALITY_AND_FUTURE_WORK.md.
    doc_path = Path("FUNCTIONALITY_AND_FUTURE_WORK.md")
    text = doc_path.read_text(encoding="utf-8")
    features: dict[str, dict[str, str]] = {}
    sections = re.split(r"\n##\s+", text)

    for sec in sections[1:]:
        lines = sec.split("\n")
        sec_title = lines[0].strip()
        sec_slug = re.sub(r"[^a-z0-9]+", "_", sec_title.lower()).strip("_")

        in_curr = True
        has_subheadings = any(line.startswith("### ") for line in lines)
        if has_subheadings:
            in_curr = False

        curr_lines: list[str] = []
        for line in lines[1:]:
            if line.startswith("### Current functionality"):
                in_curr = True
                continue
            elif line.startswith("### "):
                in_curr = False
                continue
            if in_curr:
                curr_lines.append(line)

        idx = 0
        i = 0
        while i < len(curr_lines):
            line = curr_lines[i]
            m = re.match(r"^\s*-\s+(.*)", line)
            if m:
                idx += 1
                bullet_id = f"{sec_slug}-{idx:02d}"
                full_text = m.group(1).strip()
                i += 1
                while i < len(curr_lines):
                    next_l = curr_lines[i]
                    if re.match(r"^\s*-\s+", next_l) or next_l.startswith("###") or next_l.startswith("##"):
                        break
                    if next_l.strip():
                        full_text += " " + next_l.strip()
                    i += 1
                features[bullet_id] = {
                    "section": sec_title,
                    "text": full_text[:200],
                }
            else:
                i += 1

    return features


def main() -> None:
    # Generate parity inventory files into tests/parity.
    out_dir = Path("tests/parity")
    out_dir.mkdir(parents=True, exist_ok=True)

    all_files = calc_git_file_list()

    ops_inv = calc_ops_inventory(all_files)
    with open(out_dir / "ops_inventory.json", "w", encoding="utf-8") as f:
        json.dump(ops_inv, f, indent=2)

    calls = calc_tab_calls(all_files)
    with open(out_dir / "tab_calls.json", "w", encoding="utf-8") as f:
        json.dump(calls, f, indent=2)

    qt_inv = calc_qt_inventory(all_files)
    with open(out_dir / "qt_inventory.json", "w", encoding="utf-8") as f:
        json.dump(qt_inv, f, indent=2)

    doc_feats = calc_doc_features()
    with open(out_dir / "doc_features.json", "w", encoding="utf-8") as f:
        json.dump(doc_feats, f, indent=2)

    feature_map_path = out_dir / "feature_map.json"
    if not feature_map_path.exists():
        skeleton = {feat_id: None for feat_id in doc_feats}
        with open(feature_map_path, "w", encoding="utf-8") as f:
            json.dump(skeleton, f, indent=2)

    allowlist_path = out_dir / "allowlist.json"
    if not allowlist_path.exists():
        with open(allowlist_path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)

    label_map_path = out_dir / "label_map.json"
    if not label_map_path.exists():
        with open(label_map_path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)

    print(f"Generated parity inventories. doc_features count: {len(doc_feats)}")


if __name__ == "__main__":
    main()
