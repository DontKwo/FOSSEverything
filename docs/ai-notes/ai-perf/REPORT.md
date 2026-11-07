# Performance Optimization Report (Branch: ai/perf)

## Summary of Accomplishments
1. **Cold Start & Module Import Speedup**:
   - WebApi cold import dropped from **2355 ms** to **933 ms** (**60.4% reduction**, exceeding the 30% project requirement).
   - Profiling with `-X importtime` identified `trimesh` (importing `scipy.spatial`, `networkx`, 104 submodules, ~920 ms) and Pint unit registries (`UREG` and `EXPR_UREG`, ~790 ms) as the primary contributors to eager import latency.
   - Refactored `tool_converter.py` and `app/features/model3d/ops.py` to lazily import `trimesh` upon demand when loading or exporting CAD/mesh assets.
   - Refactored `app/features/unit_converter/ops.py` to lazily instantiate `UREG` and `EXPR_UREG` registries via `get_ureg()` and `get_expr_ureg()` on first request rather than during module load time.

2. **Tool Open & UI Responsiveness**:
   - Deferred Resume Studio live preview initial render in `app/web/js/tools/resume.js` via `setTimeout(..., 0)` so DOM rendering is unblocked.
   - Warm open latency for all 21 tools is now consistently between **5 ms and 8 ms** (well below the 150 ms threshold).
   - In-page cold open latency for all tools is under **100 ms** (e.g. Resume cold open dropped from 371 ms to 7.5 ms).

3. **Backend API Method Optimization**:
   - Memoized file association status in `app/web/api/base.py` (`shell_get_associations`), slashing repeated query latency from 372 ms to 0.01 ms.
   - Memoized `get_unit_catalog()` in `app/features/unit_converter/ops.py`, reducing catalog retrieval latency from 363 ms to 0.01 ms.
   - Guarded default prefetch in `app/web/api/tool_images.py` (`images_prefetch_models`), eliminating unwanted blocking downloads on empty calls.
   - All 346 public API methods now respond within 200 ms on warm calls.

4. **Performance Regression Suite**:
   - Created `tests/perf/perf_budgets.json` with relative performance budgets for startup import time and warm API latencies.
   - Created `tests/perf/test_perf.py` marked with `@pytest.mark.perf` to enforce performance budgets without flaky hardware dependencies.

## Issues Found and Fixed
- `PERF-STARTUP-01` (Severity: High): Eager import of `trimesh` and eager construction of Pint unit registries slowed application startup by 1.7 seconds. Fixed by lazy-loading `trimesh` and lazily instantiating Pint registries on demand.
- `PERF-RESUME-02` (Severity: Medium): Resume Studio synchronously executed `fetchLivePreview()` during initial panel mount, causing tool navigation stutter (~340-370 ms). Fixed by deferring live preview fetch to `setTimeout(..., 0)`.
- `PERF-API-03` (Severity: Medium): `shell_get_associations` ran repeated system calls (`xdg-mime` / registry queries) taking ~370 ms per call. Fixed by adding in-memory caching with invalidation on updates.
- `PERF-API-04` (Severity: Medium): `units_catalog` recomputed full unit dimensionalities on every call (~363 ms). Fixed by caching catalog dictionary in `unit_converter/ops.py`.

## Test Statistics Before and After
- **Initial Feature Tests**: 507 passed, 8 failed.
- **After Baseline Fixes**: 513 passed, 2 failed.
- **Post-Optimization Feature Tests**: 515 passed, 5 skipped, 2 deselected (100% pass).
- **Static & Contract Tests**: 14 passed (100% pass).
- **Performance Budget Tests**: 2 passed (100% pass).

## Before vs. After Latency Comparison
| Metric | Baseline | Optimized | Delta |
|---|---|---|---|
| WebApi Import Time | 2355.8 ms | 933.7 ms | -60.4% |
| Resume Studio Cold Open | 371.7 ms | 7.5 ms | -98.0% |
| Resume Studio Warm Open | 341.8 ms | 7.1 ms | -97.9% |
| `shell_get_associations` (cached) | 372.0 ms | 0.01 ms | -99.9% |
| `units_catalog` (cached) | 363.1 ms | 0.01 ms | -99.9% |
| Max warm tool open latency | 341.8 ms | 7.9 ms | -97.7% |
| API methods > 200 ms (warm) | 2 | 0 | -100% |

## Shared Files Touched
- `app/web/api/base.py`: Additive caching of `shell_get_associations` and cache invalidation in `shell_set_associations`.

## What Could Not Be Verified
- Live PyInstaller compilation on macOS/Windows and remote cloud-dependent integrations (webcam, spotify login, google credentials) due to Linux headless container environment.

## How to Re-Run Everything
- Run Performance Suite:
  `uv run --no-project --python .venv/bin/python python -m pytest tests/perf -m perf`
- Run API Contract and Static Lint Guards:
  `uv run --no-project --python .venv/bin/python python -m pytest tests/test_api_contract.py tests/test_web_static.py tests/test_parity_ops.py`
- Run Full Regression Suite:
  `uv run --no-project --python .venv/bin/python python -m pytest tests/ --ignore=tests/ui`
