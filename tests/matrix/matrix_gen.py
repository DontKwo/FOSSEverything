import copy
import itertools
from pathlib import Path
import random
from typing import Any

from tests.matrix.common.fixture_factory import FixtureFactory, ALL_FAMILIES, ALL_VARIANTS

HOSTILE_STRINGS = [
    "",
    "A" * 1000,
    "unicode_test_sample",
    "../../etc/passwd",
    "C:\\Windows\\System32\\calc.exe",
    "%s%s%s%s%n",
    "{0}{1}{2}",
    "\x00nullbyte",
    "\nnewline\r\ninjection",
]

BOUNDARY_INTS = [0, -1, 1, 999999999, -999999999]
BOUNDARY_FLOATS = [0.0, -1.0, 1.0, 1e20, -1e20]


def generate_param_values(role: str, key: str, fixture_paths: list[str], temp_dir: Path) -> list[Any]:
    # Return a comprehensive list of candidate values for a given parameter role.
    if role == "input_path":
        res: list[Any] = list(fixture_paths)
        res.extend([
            str(temp_dir / "nonexistent.file"),
            str(temp_dir),
            "../../relative/traversal.txt",
            None,
            12345,
            "",
        ])
        return res

    if role == "output_path":
        res = [
            str(temp_dir / f"output_{key}.out"),
            str(temp_dir / "output space dir" / "nested.out"),
            str(temp_dir),
            None,
            12345,
            "",
            str(temp_dir / "nonexistent_dir" / "sub" / "out.txt"),
        ]
        if fixture_paths:
            res.append(fixture_paths[0])
        return res

    if role == "folder":
        return [str(temp_dir), str(temp_dir / "nonexistent_sub"), None, "", 123]

    if role == "paths_list":
        return [
            list(fixture_paths),
            [],
            [str(temp_dir / "nonexistent.txt")],
            None,
            "not_a_list",
            [123, 456],
        ]

    if role == "int":
        return [0, 1, 10, -1, None, "10", "invalid_str", [1, 2]]

    if role == "float":
        return [0.0, 1.0, 0.5, -1.0, None, "1.5", "invalid_str"]

    if role == "bool":
        return [True, False, None, "true", 0, 1]

    if role == "enum":
        return ["default", "auto", "invalid_enum_val", None, 123]

    if role == "json_blob":
        return [{}, {"test": 123}, None, "invalid_json_string", []]

    if role == "text":
        return ["test_val", "", "long_" + "a" * 200, None, 123, {"nested": True}]

    return ["val", None, 123]


def build_cases_for_method(
    meta: dict[str, Any],
    factory: FixtureFactory,
    temp_dir: Path,
    seed: int = 42,
    smoke: bool = False,
) -> list[dict[str, Any]]:
    # Generate test parameter cases for a given API method.
    cases: list[dict[str, Any]] = []
    cases.append({"_variant": "empty_dict", "params": {}})

    keys = meta.get("keys", [])
    roles = meta.get("roles", {})
    method_name = meta.get("method", "")
    accepted_kinds = meta.get("accepted_file_kinds", [])
    if not accepted_kinds:
        accepted_kinds = ["txt"]

    fixture_kinds = accepted_kinds[:2] if smoke else accepted_kinds
    variants_to_use = ["typical", "empty"] if smoke else [
        "minimal_valid", "typical", "empty", "corrupt_header",
        "wrong_ext_right_content", "special_filename", "folder_with_spaces"
    ]

    for fam in fixture_kinds:
        for var in variants_to_use:
            fix_path = str(factory.create(fam, var))
            base_params: dict[str, Any] = {}
            for k in keys:
                r = roles.get(k, "text")
                if r == "input_path":
                    if any(w in method_name for w in ("write_", "save_")):
                        base_params[k] = str(temp_dir / f"out_{fam}_{var}_{k}.{fam}")
                    else:
                        base_params[k] = fix_path
                elif r == "output_path":
                    base_params[k] = str(temp_dir / f"out_{fam}_{var}_{k}.{fam}")
                elif r == "folder":
                    base_params[k] = str(temp_dir)
                elif r == "paths_list":
                    base_params[k] = [fix_path]
                elif r == "int":
                    base_params[k] = 10
                elif r == "float":
                    base_params[k] = 1.0
                elif r == "bool":
                    base_params[k] = True
                elif r == "enum":
                    base_params[k] = "default"
                elif r == "json_blob":
                    base_params[k] = {}
                else:
                    base_params[k] = "test"

            cases.append({
                "_variant": f"{fam}_{var}_base",
                "params": dict(base_params),
                "fixture_path": fix_path,
            })

            if not smoke:
                for k in keys:
                    hostile_vals = generate_param_values(roles.get(k, "text"), k, [fix_path], temp_dir)
                    for h_val in hostile_vals[:3]:
                        mutated = dict(base_params)
                        mutated[k] = h_val
                        cases.append({
                            "_variant": f"{fam}_{var}_mut_{k}_{type(h_val).__name__}",
                            "params": mutated,
                            "fixture_path": fix_path,
                        })

    return cases
