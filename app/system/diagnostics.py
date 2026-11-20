"""Sanitized diagnostics report generator omitting sensitive paths and personal data."""
from __future__ import annotations

import datetime
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.core.tool_inventory import get_tool_inventory, validate_tool_inventory


def sanitize_path(path_str: str) -> str:
    # Replace user home directories and usernames with portable placeholders.
    if not path_str:
        return ""
    normalized = os.path.abspath(path_str).replace("\\", "/")
    home = os.path.expanduser("~").replace("\\", "/")
    if home and normalized.startswith(home):
        return normalized.replace(home, "~", 1)
    username = os.environ.get("USERNAME") or os.environ.get("USER")
    if username and username.lower() in normalized.lower():
        parts = normalized.split("/")
        cleaned = [p if p.lower() != username.lower() else "<USER>" for p in parts]
        return "/".join(cleaned)
    return normalized


def _probe_tool_version(binary_path: str, arg: str = "--version") -> str | None:
    # Safely probe binary version output within a strict 3-second timeout.
    try:
        proc = subprocess.run(
            [binary_path, arg],
            capture_output=True,
            text=True,
            timeout=3.0,
            check=False,
        )
        line = (proc.stdout or proc.stderr).splitlines()
        return line[0].strip() if line else None
    except Exception:
        return None


def check_external_dependencies() -> dict[str, dict[str, Any]]:
    # Query installed external tools required for optional features.
    dependencies: dict[str, tuple[list[str], str, str]] = {
        "ffmpeg": (["ffmpeg"], "-version", "Required for video transcoding and media timelines"),
        "tesseract": (["tesseract"], "--version", "Required for offline OCR extraction"),
        "libreoffice": (["soffice", "libreoffice"], "--version", "Required for office doc to PDF conversion"),
        "pandoc": (["pandoc"], "--version", "Required for markdown/docx document conversions"),
        "calibre": (["ebook-convert"], "--version", "Required for EPUB/MOBI conversion"),
        "ghostscript": (["gs", "gswin64c", "gswin32c"], "--version", "Optional accelerator for PDF rasterization"),
        "yt-dlp": (["yt-dlp", "yt_dlp"], "--version", "Optional for online playlist track fetching"),
    }

    results: dict[str, dict[str, Any]] = {}
    for dep_name, (candidates, ver_flag, description) in dependencies.items():
        found_bin: str | None = None
        for cand in candidates:
            loc = shutil.which(cand)
            if loc:
                found_bin = loc
                break
        if found_bin:
            version_str = _probe_tool_version(found_bin, ver_flag)
            results[dep_name] = {
                "available": True,
                "path": sanitize_path(found_bin),
                "version": version_str or "Detected",
                "description": description,
            }
        else:
            results[dep_name] = {
                "available": False,
                "path": None,
                "version": None,
                "description": description,
            }
    return results


def generate_diagnostics_report() -> dict[str, Any]:
    # Produce a sanitized operational diagnostics report for debugging and audits.
    inventory = get_tool_inventory()
    inv_check = validate_tool_inventory()
    deps = check_external_dependencies()

    return {
        "schema_version": "1.0.0",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "runtime": {
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "in_virtual_env": bool(sys.prefix != sys.base_prefix),
        },
        "tool_inventory": {
            "total_tools": len(inventory),
            "validated": inv_check["valid"],
            "tools": [{"id": t.id, "name": t.name, "category": t.category, "destructive_risk": t.destructive_risk} for t in inventory],
        },
        "dependencies": deps,
    }


def export_diagnostics_json(output_path: str | None = None) -> str:
    # Export sanitized diagnostics report as a formatted JSON string or file.
    report = generate_diagnostics_report()
    payload = json.dumps(report, indent=2)
    if output_path:
        out = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(payload)
    return payload
