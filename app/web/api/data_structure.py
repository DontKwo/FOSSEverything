import csv
import io
import json
import os
import tomllib
import xml.etree.ElementTree as ET
from typing import Any

import yaml

from app.web.api.hdf5_reader import inspect_hdf5, is_hdf5_file


def inspect_data_structure(
    file_path: str | None = None,
    content: str | None = None,
    format_hint: str | None = None,
) -> dict[str, Any]:
    # Parse file or string content into a hierarchical structure tree with metadata.
    if file_path:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        if is_hdf5_file(file_path) or file_path.lower().endswith((".h5", ".hdf5", ".he5")):
            return _inspect_hdf5_structure(file_path)

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

    if content is None:
        raise ValueError("Either file_path or content must be provided.")

    fmt = (format_hint or "auto").lower()
    parsed_data, detected_fmt = _parse_content(content, fmt)

    stats = {
        "total_nodes": 0,
        "max_depth": 0,
        "types_breakdown": {},
    }
    root_node = _build_tree_node("root", parsed_data, "$", 0, stats)

    return {
        "format": detected_fmt.upper(),
        "file_path": file_path,
        "file_size": len(content.encode("utf-8")),
        "root": root_node,
        "stats": {
            "total_nodes": stats["total_nodes"],
            "max_depth": stats["max_depth"],
            "types_breakdown": stats["types_breakdown"],
        },
    }


def _inspect_hdf5_structure(file_path: str) -> dict[str, Any]:
    # Wrap HDF5 inspection result into common hierarchical tree structure.
    raw = inspect_hdf5(file_path)
    file_size = raw.get("file_size", os.path.getsize(file_path))

    def convert_h5_node(node: dict[str, Any], path: str, depth: int, stats: dict[str, Any]) -> dict[str, Any]:
        stats["total_nodes"] += 1
        stats["max_depth"] = max(stats["max_depth"], depth)
        ntype = node.get("type", "group")
        stats["types_breakdown"][ntype] = stats["types_breakdown"].get(ntype, 0) + 1

        children: list[dict[str, Any]] = []
        for child in node.get("children", []):
            child_name = child.get("name", "item")
            child_path = f"{path}/{child_name}".replace("//", "/")
            children.append(convert_h5_node(child, child_path, depth + 1, stats))

        # Include attributes as child nodes if present.
        for ak, av in node.get("attributes", {}).items():
            stats["total_nodes"] += 1
            stats["types_breakdown"]["attribute"] = stats["types_breakdown"].get("attribute", 0) + 1
            children.append({
                "name": f"@{ak}",
                "type": "attribute",
                "path": f"{path}/@{ak}",
                "value": str(av),
                "length": len(str(av)),
                "preview": str(av),
                "children": [],
            })

        preview = node.get("preview")
        if not preview and ntype == "group":
            preview = f"{len(children)} members"
        elif not preview and ntype == "dataset":
            preview = f"shape={node.get('shape')} dtype={node.get('dtype')}"

        return {
            "name": node.get("name", "/"),
            "type": ntype,
            "path": path,
            "shape": node.get("shape"),
            "dtype": node.get("dtype"),
            "size_bytes": node.get("size_bytes"),
            "value": str(preview),
            "length": len(children),
            "preview": str(preview),
            "children": children,
        }

    stats = {
        "total_nodes": 0,
        "max_depth": 0,
        "types_breakdown": {},
    }
    root = convert_h5_node(raw.get("root", {}), "/", 0, stats)

    return {
        "format": "HDF5",
        "file_path": file_path,
        "file_size": file_size,
        "root": root,
        "stats": {
            "total_nodes": stats["total_nodes"],
            "max_depth": stats["max_depth"],
            "types_breakdown": stats["types_breakdown"],
            "groups_count": raw.get("summary", {}).get("groups_count", 0),
            "datasets_count": raw.get("summary", {}).get("datasets_count", 0),
            "attributes_count": raw.get("summary", {}).get("attributes_count", 0),
        },
    }


def _parse_content(content: str, fmt: str) -> tuple[Any, str]:
    # Attempt parsing content using specified format or auto-detection.
    trimmed = content.strip()
    if fmt in ("auto", "json") and (trimmed.startswith(("{", "[")) or fmt == "json"):
        try:
            return json.loads(trimmed), "json"
        except Exception:
            if fmt == "json":
                raise

    if fmt in ("auto", "xml") and (trimmed.startswith("<") or fmt == "xml"):
        try:
            root = ET.fromstring(trimmed)
            return _xml_to_dict(root), "xml"
        except Exception:
            if fmt == "xml":
                raise

    if fmt in ("auto", "yaml", "yml"):
        try:
            parsed = yaml.safe_load(trimmed)
            if isinstance(parsed, (dict, list)):
                return parsed, "yaml"
        except Exception:
            if fmt in ("yaml", "yml"):
                raise

    if fmt in ("auto", "toml"):
        try:
            return tomllib.loads(trimmed), "toml"
        except Exception:
            if fmt == "toml":
                raise

    # Test CSV or tabular data.
    if "\n" in trimmed or "," in trimmed or "\t" in trimmed:
        try:
            sample = trimmed[:2048]
            dialect = csv.Sniffer().sniff(sample)
            reader = list(csv.reader(io.StringIO(trimmed), dialect))
            if reader and len(reader) > 1:
                headers = reader[0]
                rows = [dict(zip(headers, row)) for row in reader[1:]]
                return rows, "csv"
        except Exception:
            # Fallback when CSV sniffing fails.
            sample = ""

    # Fallback to lines of text.
    return [line for line in trimmed.splitlines() if line], "text"


def _xml_to_dict(elem: ET.Element) -> dict[str, Any]:
    # Convert XML element tree into nested dictionary representation.
    res: dict[str, Any] = {}
    if elem.attrib:
        for k, v in elem.attrib.items():
            res[f"@{k}"] = v
    for child in elem:
        child_res = _xml_to_dict(child)
        if child.tag in res:
            if not isinstance(res[child.tag], list):
                res[child.tag] = [res[child.tag]]
            res[child.tag].append(child_res)
        else:
            res[child.tag] = child_res
    if elem.text and elem.text.strip():
        text_val = elem.text.strip()
        if not res:
            return {"#text": text_val}
        res["#text"] = text_val
    return res


def _build_tree_node(
    name: str, val: Any, path: str, depth: int, stats: dict[str, Any]
) -> dict[str, Any]:
    # Recursively construct uniform tree node dict with type badges and value summaries.
    stats["total_nodes"] += 1
    stats["max_depth"] = max(stats["max_depth"], depth)

    if isinstance(val, dict):
        stats["types_breakdown"]["object"] = stats["types_breakdown"].get("object", 0) + 1
        children = []
        for k, v in val.items():
            child_path = f"{path}.{k}"
            children.append(_build_tree_node(str(k), v, child_path, depth + 1, stats))
        return {
            "name": name,
            "type": "object",
            "path": path,
            "value": f"{len(children)} keys",
            "length": len(children),
            "preview": "{" + ", ".join(list(val.keys())[:3]) + ("..." if len(val) > 3 else "") + "}",
            "children": children,
        }

    if isinstance(val, list):
        stats["types_breakdown"]["array"] = stats["types_breakdown"].get("array", 0) + 1
        children = []
        for idx, item in enumerate(val):
            child_path = f"{path}[{idx}]"
            children.append(_build_tree_node(f"[{idx}]", item, child_path, depth + 1, stats))
        return {
            "name": name,
            "type": "array",
            "path": path,
            "value": f"{len(children)} items",
            "length": len(children),
            "preview": f"Array of {len(val)} elements",
            "children": children,
        }

    # Primitive types.
    val_type = "string"
    if isinstance(val, bool):
        val_type = "boolean"
    elif isinstance(val, int):
        val_type = "integer"
    elif isinstance(val, float):
        val_type = "float"
    elif val is None:
        val_type = "null"

    stats["types_breakdown"][val_type] = stats["types_breakdown"].get(val_type, 0) + 1
    str_val = "null" if val is None else str(val)

    return {
        "name": name,
        "type": val_type,
        "path": path,
        "value": str_val,
        "length": len(str_val),
        "preview": str_val[:80] + ("..." if len(str_val) > 80 else ""),
        "children": [],
    }
