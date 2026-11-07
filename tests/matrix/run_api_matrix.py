import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any

import psutil

from app.web.api import WebApi
from tests.matrix.common.fixture_factory import FixtureFactory
from tests.matrix.matrix_gen import build_cases_for_method
from tests.matrix.oracles import check_case_oracles, patch_network_blocking, unpatch_network_blocking

ENV_DEPENDENT_METHODS = {
    "ocr_": "tesseract",
    "rembg_": "rembg_models",
    "spotify_": "spotify_credentials",
    "google_": "google_credentials",
    "webcam_": "webcam",
}


def is_env_dependent(method_name: str) -> tuple[bool, str]:
    # Check if a method requires specific environment dependencies.
    for prefix, dep in ENV_DEPENDENT_METHODS.items():
        if method_name.startswith(prefix):
            return True, dep
    return False, ""


def execute_case_worker(api: WebApi, method_name: str, params: dict[str, Any]) -> dict[str, Any]:
    # Call method on WebApi safely catching any unhandled exceptions.
    fn = getattr(api, method_name, None)
    if not fn:
        return {"ok": False, "error": f"Method {method_name} not found"}
    try:
        return fn(params)
    except Exception as exc:
        return {"ok": False, "error": f"Unhandled exception: {exc}"}


def run_matrix(
    tool_filter: str | None = None,
    method_filter: str | None = None,
    fixture_kind_filter: str | None = None,
    seed: int = 42,
    shard_str: str | None = None,
    smoke: bool = False,
    failed_only: bool = False,
    max_seconds: float = 300.0,
    out_dir: Path | str = "tests/matrix/results",
) -> dict[str, Any]:
    # Main matrix test runner executing generated cases against WebApi.
    patch_network_blocking()
    start_time = time.time()
    out_p = Path(out_dir)
    out_p.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_p / "results.jsonl"
    summary_path = out_p / "summary.md"

    inv_path = Path("tests/matrix/api_inventory.json")
    if not inv_path.exists():
        unpatch_network_blocking()
        raise FileNotFoundError("tests/matrix/api_inventory.json not found")

    with open(inv_path, "r", encoding="utf-8") as f:
        inventory = json.load(f)

    shard_idx, shard_total = 1, 1
    if shard_str and "/" in shard_str:
        p1, p2 = shard_str.split("/", 1)
        shard_idx, shard_total = int(p1), int(p2)

    methods = sorted(list(inventory.keys()))
    if tool_filter:
        methods = [m for m in methods if inventory[m].get("tool") == tool_filter]
    if method_filter:
        methods = [m for m in methods if method_filter in m]

    methods_for_shard = [m for i, m in enumerate(methods) if (i % shard_total) == (shard_idx - 1)]

    api = WebApi()
    total_cases = 0
    passed_cases = 0
    failed_cases = 0
    skipped_cases = 0
    failures_by_signature: dict[str, list[dict[str, Any]]] = {}

    with tempfile.TemporaryDirectory() as td:
        work_dir = Path(td)
        os.environ["FOSS_SETTINGS_DIR"] = str(work_dir / "settings")
        factory = FixtureFactory(work_dir / "fixtures", seed=seed)

        with open(jsonl_path, "w", encoding="utf-8") as jsonl_file:
            for method_name in methods_for_shard:
                meta = inventory[method_name]
                env_dep, dep_name = is_env_dependent(method_name)

                cases = build_cases_for_method(meta, factory, work_dir, seed=seed, smoke=smoke)
                if fixture_kind_filter:
                    cases = [c for c in cases if fixture_kind_filter in c.get("_variant", "")]

                for case in cases:
                    if (time.time() - start_time) > max_seconds:
                        break

                    total_cases += 1
                    var_name = case.get("_variant", "unknown")
                    params = case.get("params", {})
                    fix_path = case.get("fixture_path")

                    input_hashes: dict[str, str] = {}
                    if fix_path and Path(fix_path).exists():
                        input_hashes[fix_path] = hashlib.sha256(Path(fix_path).read_bytes()).hexdigest()

                    out_paths: list[str] = []
                    for k, v in params.items():
                        if meta.get("roles", {}).get(k) == "output_path" and isinstance(v, str):
                            out_paths.append(v)

                    t0 = time.time()
                    res = execute_case_worker(api, method_name, params)
                    dur = round(time.time() - t0, 4)

                    ok_oracle, oracle_msg = check_case_oracles(res, input_hashes, out_paths)

                    status = "pass"
                    if not ok_oracle:
                        status = "fail"
                        failed_cases += 1
                        sig = f"{method_name}::{oracle_msg}"
                        if sig not in failures_by_signature:
                            failures_by_signature[sig] = []
                        failures_by_signature[sig].append({
                            "method": method_name,
                            "variant": var_name,
                            "params": params,
                            "msg": oracle_msg,
                            "res": res,
                        })
                    else:
                        passed_cases += 1

                    record = {
                        "method": method_name,
                        "variant": var_name,
                        "status": status,
                        "duration": dur,
                        "message": oracle_msg,
                    }
                    jsonl_file.write(json.dumps(record) + "\n")
                    jsonl_file.flush()

    unpatch_network_blocking()
    total_time = round(time.time() - start_time, 2)
    summary_lines = [
        "# Matrix Run Summary",
        f"- **Total Generated & Run**: {total_cases}",
        f"- **Passed**: {passed_cases}",
        f"- **Failed**: {failed_cases}",
        f"- **Skipped**: {skipped_cases}",
        f"- **Execution Time**: {total_time}s",
        "",
        "## Root Causes & Failures",
    ]
    if not failures_by_signature:
        summary_lines.append("No failures found. Matrix run is clean.")
    else:
        for sig, items in failures_by_signature.items():
            summary_lines.append(f"### {sig} ({len(items)} occurrences)")
            ex = items[0]
            summary_lines.append(f"- Example: `{ex['method']}` variant `{ex['variant']}`")
            summary_lines.append(f"- Message: `{ex['msg']}`")
            summary_lines.append(f"- Result: `{ex['res']}`")
            summary_lines.append("")

    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    return {
        "total": total_cases,
        "passed": passed_cases,
        "failed": failed_cases,
        "skipped": skipped_cases,
        "time": total_time,
        "summary": str(summary_path),
        "failures": failures_by_signature,
    }


def main() -> None:
    # CLI entry point for matrix testing runner.
    parser = argparse.ArgumentParser(description="Run WebApi Automated Matrix Tests")
    parser.add_argument("--tool", type=str, default=None, help="Filter by tool name")
    parser.add_argument("--method", type=str, default=None, help="Filter by method name")
    parser.add_argument("--fixture-kind", type=str, default=None, help="Filter by fixture kind")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--shard", type=str, default=None, help="Shard string like 1/4")
    parser.add_argument("--smoke", action="store_true", help="Run fast smoke subset")
    parser.add_argument("--failed-only", action="store_true", help="Run only previously failed cases")
    parser.add_argument("--max-seconds", type=float, default=120.0, help="Max run duration")
    args = parser.parse_args()

    res = run_matrix(
        tool_filter=args.tool,
        method_filter=args.method,
        fixture_kind_filter=args.fixture_kind,
        seed=args.seed,
        shard_str=args.shard,
        smoke=args.smoke,
        failed_only=args.failed_only,
        max_seconds=args.max_seconds,
    )
    print(f"Matrix run complete in {res['time']}s: {res['passed']} passed, {res['failed']} failed.")
    if res["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
