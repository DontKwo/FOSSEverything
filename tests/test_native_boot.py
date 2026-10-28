import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

if sys.platform == "win32":
    import winreg  # noqa: 22


def calc_is_webview2_available() -> bool:
    # Check if WebView2 runtime is present on Windows.
    if sys.platform != "win32":
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-F301-4475-A00D-019777DE8DFE}",
        )
        pv_val, _ = winreg.QueryValueEx(key, "pv")
        return bool(pv_val)
    except Exception:  # noqa: 10
        pass
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\EdgeUpdate\Clients\{F3017226-F301-4475-A00D-019777DE8DFE}",
        )
        user_pv_val, _ = winreg.QueryValueEx(key, "pv")
        return bool(user_pv_val)
    except Exception:
        return True


@pytest.mark.native
def test_native_boot(tmp_path: Path) -> None:
    # Launch main application in native pywebview window and verify selftest.
    if sys.platform != "win32" or not calc_is_webview2_available():
        pytest.skip("Native boot requires Windows with WebView2")

    out_file = tmp_path / "selftest_out.json"
    env = os.environ.copy()
    env["FOSS_SELFTEST_OUT"] = str(out_file)

    cmd = [sys.executable, "main.py", "--selftest"]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=90)

    assert proc.returncode == 0, f"main.py --selftest failed with code {proc.returncode}: {proc.stderr}"
    assert out_file.exists(), "Selftest output file was not created"

    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data.get("ready") is True, f"Selftest reported not ready: {data}"
    assert len(data.get("missing_api", [])) == 0, f"Missing API methods: {data.get('missing_api')}"
    errors = [f for f in data.get("findings", []) if f.get("severity") == "error"]
    assert len(errors) == 0, f"Selftest reported errors: {errors}"
