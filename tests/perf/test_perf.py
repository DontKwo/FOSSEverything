import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any
import pytest

from app.web.api import WebApi

BUDGET_FILE = Path(__file__).parent / "perf_budgets.json"


def load_budgets() -> dict[str, Any]:
    # Load performance budgets from JSON definition.
    return json.loads(BUDGET_FILE.read_text(encoding="utf-8"))


@pytest.mark.perf
def test_webapi_import_budget() -> None:
    # Assert cold import time of app.web.api remains within budget.
    budgets = load_budgets()
    max_ms = float(budgets.get("max_webapi_import_ms", 1500))
    code = "import time; t0 = time.perf_counter(); import app.web.api; print((time.perf_counter()-t0)*1000)"
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    import_ms = float(res.stdout.strip().split("\n")[-1])
    assert import_ms < max_ms, f"app.web.api import time {import_ms:.2f}ms exceeded budget {max_ms:.2f}ms"


@pytest.mark.perf
def test_warm_api_methods_budget() -> None:
    # Assert all warm API methods respond under the budget threshold.
    budgets = load_budgets()
    max_ms = float(budgets.get("max_warm_api_call_ms", 200))
    api = WebApi()
    methods = [m for m in dir(api) if not m.startswith("_") and callable(getattr(api, m))]
    assert len(methods) >= 300

    # Warm up methods excluding state resets
    for m in methods:
        if m != "shell_set_associations":
            getattr(api, m)({})

    slow: list[tuple[str, float]] = []
    for m in methods:
        if m == "shell_set_associations":
            continue
        fn = getattr(api, m)
        t0 = time.perf_counter()
        fn({})
        dt = (time.perf_counter() - t0) * 1000
        if dt > max_ms:
            slow.append((m, dt))

    assert not slow, f"Warm API methods exceeded budget ({len(slow)}): {slow}"
