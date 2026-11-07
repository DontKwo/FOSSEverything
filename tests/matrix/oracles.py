import hashlib
import json
import os
from pathlib import Path
import socket
from typing import Any
import xml.etree.ElementTree as ET
import zipfile

from PIL import Image
import pymupdf
import trimesh
import yaml

_ORIGINAL_CONNECT = socket.socket.connect


def patch_network_blocking() -> None:
    # Block outbound network connections except loopback 127.0.0.1.
    def guarded_connect(self: socket.socket, address: Any) -> None:
        host = address[0] if isinstance(address, tuple) and len(address) > 0 else str(address)
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise PermissionError(f"Network call blocked to {host}")
        return _ORIGINAL_CONNECT(self, address)

    socket.socket.connect = guarded_connect  # type: ignore[assignment]


def unpatch_network_blocking() -> None:
    # Restore standard socket connect behavior.
    socket.socket.connect = _ORIGINAL_CONNECT  # type: ignore[assignment]


def verify_file_validity(path: Path) -> tuple[bool, str]:
    # Check if a generated output file opens cleanly with an independent reader.
    if not path.exists():
        return False, "File does not exist"
    if path.stat().st_size == 0:
        return False, "File is 0 bytes"

    ext = path.suffix.lower().lstrip(".")
    try:
        if ext == "pdf":
            doc = pymupdf.open(str(path))
            pages = len(doc)
            doc.close()
            return (True, f"PDF valid ({pages} pages)") if pages >= 1 else (False, "Empty PDF")
        if ext in ("png", "jpg", "jpeg", "webp", "bmp", "tiff", "gif"):
            with Image.open(str(path)) as im:
                im.verify()
            return True, "Image valid"
        if ext in ("zip", "docx", "xlsx", "pptx", "epub"):
            with zipfile.ZipFile(str(path)) as zf:
                bad = zf.testzip()
                if bad:
                    return False, f"Corrupted zip entry {bad}"
            return True, "Zip container valid"
        if ext in ("stl", "obj", "ply", "gltf"):
            m = trimesh.load(str(path))
            return True, "3D mesh loaded"
        if ext == "json":
            json.loads(path.read_text(encoding="utf-8"))
            return True, "JSON valid"
        if ext in ("yaml", "yml"):
            yaml.safe_load(path.read_text(encoding="utf-8"))
            return True, "YAML valid"
        if ext == "xml":
            ET.fromstring(path.read_text(encoding="utf-8"))
            return True, "XML valid"
        if ext in ("txt", "md", "csv", "tsv", "sql", "js", "css"):
            path.read_text(encoding="utf-8", errors="replace")
            return True, "Text readable"
        return True, "File readable"
    except Exception as exc:
        return False, f"Validator failed for {ext}: {exc}"


def check_case_oracles(
    result: Any,
    input_hashes_before: dict[str, str],
    output_paths_expected: list[str],
    is_job: bool = False,
) -> tuple[bool, str]:
    # Verify strict test case contract assertions.
    if not isinstance(result, dict):
        return False, f"Result is not dict: {type(result)}"
    if "ok" not in result or not isinstance(result["ok"], bool):
        return False, "Result missing boolean 'ok' key"

    if not result["ok"]:
        err = result.get("error")
        if not err or not isinstance(err, str) or not err.strip():
            return False, "Failure response missing non-empty error string"
        bad_words = ("Traceback", "undefined", "[object Object]")
        for bw in bad_words:
            if bw in err:
                return False, f"Error contains forbidden text '{bw}'"
        return True, "Error handled cleanly"

    for path_str, orig_hash in input_hashes_before.items():
        inp = Path(path_str)
        if inp.exists():
            curr_hash = hashlib.sha256(inp.read_bytes()).hexdigest()
            if curr_hash != orig_hash:
                return False, f"Input file {inp} was modified in-place"

    for out_str in output_paths_expected:
        out_p = Path(out_str)
        ok_valid, msg = verify_file_validity(out_p)
        if not ok_valid:
            return False, f"Output file invalid: {msg}"

    return True, "Passed all oracles"
