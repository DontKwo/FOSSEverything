import csv
import itertools
import json
import math
import os
from collections import deque
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import h5py

import numpy as np

MAX_CHILDREN_PAGE = 500
MAX_PREVIEW_ROWS = 500
MAX_PREVIEW_COLS = 100
MAX_PREVIEW_CELLS = 20000
MAX_STAT_ELEMENTS = 2_000_000
MAX_EXPORT_ELEMENTS = 5_000_000
MAX_TREE_NODES = 5000
MAX_SEARCH_VISITS = 50000
MAX_ATTR_ELEMENTS = 256

H5_ERRORS = (OSError, ValueError, TypeError, KeyError, RuntimeError, NotImplementedError, AttributeError)


class Hdf5Error(ValueError):
    pass


def is_hdf5_file(file_path: str) -> bool:
    import h5py
            # Check the HDF5 signature with h5py.
    try:
        return bool(os.path.isfile(file_path) and h5py.is_hdf5(file_path))
    except H5_ERRORS:
        return False


def _open_file(file_path: str) -> 'h5py.File':
    import h5py
            # Open a file read-only or raise a clean Hdf5Error.
    if not os.path.exists(file_path):
        raise Hdf5Error(f"File not found: {file_path}")
    if not is_hdf5_file(file_path):
        raise Hdf5Error(f"Not a valid HDF5 file: {os.path.basename(file_path)}")
    try:
        return h5py.File(file_path, "r")
    except H5_ERRORS as exc:
        raise Hdf5Error(f"Cannot open HDF5 file: {exc}") from exc


def _norm_path(path: Any) -> str:
    # Normalize a user path into an absolute HDF5 path.
    text = str(path or "/").strip().replace("\\", "/")
    parts = [part for part in text.split("/") if part]
    return "/" + "/".join(parts)


def _join_path(parent: str, name: str) -> str:
    # Join a parent group path and a member name.
    return "/" + name if parent == "/" else parent + "/" + name


def _finite_or_text(value: float) -> Any:
    # Keep finite floats numeric and turn nan or inf into text.
    return value if math.isfinite(value) else str(value)


def _ref_text(ref: Any, hf: Any) -> str:
    # Describe an object or region reference by its target path.
    if not ref:
        return "<null reference>"
    if hf is None:
        return "<reference>"
    try:
        return "ref:" + str(hf[ref].name)
    except H5_ERRORS:
        return "<dangling reference>"


def _json_value(value: Any, hf: Any = None) -> Any:
    import h5py
            # Convert numpy and h5py values into JSON-safe primitives.
    if isinstance(value, h5py.Empty):
        return "<empty>"
    if isinstance(value, (bytes, np.bytes_)):
        return bytes(value).decode("utf-8", errors="replace")
    if isinstance(value, str):
        return str(value)
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return _finite_or_text(float(value))
    if isinstance(value, (complex, np.complexfloating)):
        cval = complex(value)
        return f"{cval.real:g}{cval.imag:+g}j"
    if isinstance(value, h5py.Reference):
        return _ref_text(value, hf)
    if isinstance(value, np.void):
        names = value.dtype.names
        if names:
            return {name: _json_value(value[name], hf) for name in names}
        return bytes(value).hex()
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return _json_value(value[()], hf)
        return [_json_value(item, hf) for item in value]
    if isinstance(value, (list, tuple)):
        return [_json_value(item, hf) for item in value]
    return str(value)


def _describe_dtype(dt: np.dtype) -> dict[str, Any]:
    import h5py
            # Describe a dtype with kind, label, and enum or compound details.
    string_info = h5py.check_string_dtype(dt)
    enum_map = h5py.check_enum_dtype(dt)
    vlen_base = h5py.check_vlen_dtype(dt)
    ref_kind = h5py.check_ref_dtype(dt)
    info: dict[str, Any] = {"itemsize": int(dt.itemsize)}
    if string_info is not None:
        if string_info.length is None:
            info.update(kind="vlen_string", label=f"vlen string ({string_info.encoding})")
        else:
            info.update(kind="fixed_string", label=f"string[{string_info.length}] ({string_info.encoding})")
    elif enum_map is not None:
        pairs = sorted(enum_map.items(), key=lambda pair: pair[1])
        info.update(kind="enum", label=f"enum<{dt.name}>", enum={name: int(member) for name, member in pairs})
    elif ref_kind is not None:
        info.update(kind="reference", label="region reference" if ref_kind is h5py.RegionReference else "object reference")
    elif vlen_base is not None:
        info.update(kind="vlen", label=f"vlen {np.dtype(vlen_base).name}")
    elif dt.names:
        fields = []
        for name in dt.names:
            sub = _describe_dtype(dt.fields[name][0])
            fields.append({"name": name, "kind": sub["kind"], "dtype": sub["label"], "offset": int(dt.fields[name][1])})
        info.update(kind="compound", label="compound{" + ", ".join(f"{f['name']}: {f['dtype']}" for f in fields) + "}", fields=fields)
    elif dt.subdtype is not None:
        base, sub_shape = dt.subdtype
        info.update(kind="array", label=f"array{list(sub_shape)} of {_describe_dtype(base)['label']}")
    elif dt.kind == "b":
        info.update(kind="bool", label="bool")
    elif dt.kind == "i":
        info.update(kind="integer", label=dt.name)
    elif dt.kind == "u":
        info.update(kind="unsigned", label=dt.name)
    elif dt.kind == "f":
        info.update(kind="float", label=dt.name)
    elif dt.kind == "c":
        info.update(kind="complex", label=dt.name)
    elif dt.kind == "V":
        info.update(kind="opaque", label=f"opaque[{dt.itemsize}]")
    else:
        info.update(kind="other", label=str(dt))
    if dt.byteorder in ("<", ">"):
        info["byte_order"] = "little" if dt.byteorder == "<" else "big"
    return info


def _read_attributes(obj: Any, hf: Any) -> list[dict[str, Any]]:
    import h5py
            # Read every attribute of an object, clipping large arrays.
    items: list[dict[str, Any]] = []
    for name in obj.attrs.keys():
        entry: dict[str, Any] = {"name": str(name)}
        try:
            attr_id = obj.attrs.get_id(name)
            dtype_info = _describe_dtype(attr_id.dtype)
            entry["dtype"] = dtype_info["label"]
            entry["kind"] = dtype_info["kind"]
            entry["shape"] = list(attr_id.shape) if attr_id.shape is not None else []
            value = obj.attrs[name]
            if isinstance(value, np.ndarray) and value.size > MAX_ATTR_ELEMENTS:
                entry["truncated"] = True
                entry["total_elements"] = int(value.size)
                value = value.reshape(-1)[:MAX_ATTR_ELEMENTS]
            entry["value"] = _json_value(value, hf)
        except H5_ERRORS as exc:
            entry["error"] = str(exc)
        items.append(entry)
    return items


def _link_info(grp: Any, name: str) -> dict[str, Any]:
    import h5py
            # Describe how a member is linked into its parent group.
    link = grp.get(name, getlink=True)
    if isinstance(link, h5py.SoftLink):
        return {"type": "soft", "target": link.path}
    if isinstance(link, h5py.ExternalLink):
        return {"type": "external", "target": link.path, "filename": link.filename}
    return {"type": "hard"}


def _resolve(grp: Any, name: str) -> Any:
    # Open a member, returning None for broken links.
    try:
        return grp.get(name)
    except H5_ERRORS:
        return None


def _summarize(parent_path: str, name: str, obj: Any, link: dict[str, Any]) -> dict[str, Any]:
    import h5py
            # Build the compact tree row for one member.
    node: dict[str, Any] = {"name": name, "path": _join_path(parent_path, name), "link": link, "broken": obj is None}
    if obj is None:
        node.update(kind="link", expandable=False)
    elif isinstance(obj, h5py.Group):
        node.update(kind="group", members=len(obj), expandable=len(obj) > 0, attribute_count=len(obj.attrs))
    elif isinstance(obj, h5py.Dataset):
        shape = list(obj.shape) if obj.shape is not None else None
        node.update(kind="dataset", expandable=False, shape=shape, dtype=_describe_dtype(obj.dtype)["label"], attribute_count=len(obj.attrs))
    else:
        node.update(kind="datatype", expandable=False, attribute_count=len(obj.attrs))
    return node


def _get_group(hf: Any, path: str) -> Any:
    import h5py
            # Open a group by path or raise Hdf5Error.
    try:
        obj = hf[path]
    except H5_ERRORS as exc:
        raise Hdf5Error(f"Path not found: {path}") from exc
    if not isinstance(obj, h5py.Group):
        raise Hdf5Error(f"Not a group: {path}")
    return obj


def _get_dataset(hf: Any, path: str) -> Any:
    import h5py
            # Open a dataset by path or raise Hdf5Error.
    try:
        obj = hf[path]
    except H5_ERRORS as exc:
        raise Hdf5Error(f"Path not found: {path}") from exc
    if not isinstance(obj, h5py.Dataset):
        raise Hdf5Error(f"Not a dataset: {path}")
    return obj


def open_hdf5(file_path: str) -> dict[str, Any]:
    # Return file level metadata plus the first page of root members.
    with _open_file(file_path) as hf:
        root = list_hdf5_children(file_path, "/")
        return {
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "userblock_size": int(hf.userblock_size),
            "libver": [str(v) for v in hf.libver],
            "attributes": _read_attributes(hf, hf),
            "root": root,
            "h5py_version": h5py.__version__,
        }


def list_hdf5_children(file_path: str, path: str = "/", offset: int = 0, limit: int = MAX_CHILDREN_PAGE) -> dict[str, Any]:
    # Return one page of member summaries for a group.
    norm = _norm_path(path)
    start = max(0, int(offset))
    page = max(1, min(int(limit), MAX_CHILDREN_PAGE))
    with _open_file(file_path) as hf:
        grp = _get_group(hf, norm)
        total = len(grp)
        children = []
        for name in itertools.islice(iter(grp), start, start + page):
            children.append(_summarize(norm, name, _resolve(grp, name), _link_info(grp, name)))
    return {"path": norm, "total": total, "offset": start, "children": children, "has_more": start + len(children) < total}


def _dataset_details(ds: Any, hf: Any) -> dict[str, Any]:
    import h5py
            # Collect shape, storage, filter, and dtype properties of a dataset.
    desc = _describe_dtype(ds.dtype)
    plist = ds.id.get_create_plist()
    layouts = {h5py.h5d.COMPACT: "compact", h5py.h5d.CONTIGUOUS: "contiguous", h5py.h5d.CHUNKED: "chunked", h5py.h5d.VIRTUAL: "virtual"}
    filters = []
    for index in range(plist.get_nfilters()):
        code, _flags, values, fname = plist.get_filter(index)
        filters.append({"id": int(code), "name": bytes(fname).decode("utf-8", errors="replace"), "options": [int(v) for v in values]})
    details: dict[str, Any] = {
        "dtype": desc,
        "shape": list(ds.shape) if ds.shape is not None else None,
        "maxshape": ["unlimited" if m is None else int(m) for m in ds.maxshape] if ds.maxshape is not None else None,
        "ndim": len(ds.shape) if ds.shape is not None else 0,
        "elements": int(ds.size) if ds.size is not None else 0,
        "nbytes": int(ds.nbytes) if ds.size is not None else 0,
        "storage_bytes": int(ds.id.get_storage_size()),
        "layout": layouts.get(plist.get_layout(), "unknown"),
        "chunks": list(ds.chunks) if ds.chunks else None,
        "compression": ds.compression,
        "compression_opts": _json_value(ds.compression_opts) if ds.compression_opts is not None else None,
        "shuffle": bool(ds.shuffle),
        "fletcher32": bool(ds.fletcher32),
        "scaleoffset": ds.scaleoffset,
        "filters": filters,
        "external": [{"file": str(item[0]), "offset": int(item[1]), "size": int(item[2])} for item in ds.external] if ds.external else [],
        "fields": desc.get("fields", []),
    }
    try:
        details["fillvalue"] = _json_value(ds.fillvalue, hf)
    except H5_ERRORS:
        details["fillvalue"] = None
    return details


def describe_hdf5_node(file_path: str, path: str = "/") -> dict[str, Any]:
    # Return full details for a group, dataset, committed datatype, or link.
    norm = _norm_path(path)
    with _open_file(file_path) as hf:
        if norm == "/":
            link: dict[str, Any] = {"type": "root"}
            obj: Any = hf
            name = "/"
        else:
            parent_path, name = norm.rsplit("/", 1)
            parent = _get_group(hf, parent_path or "/")
            if parent.get(name, getlink=True) is None:
                raise Hdf5Error(f"Path not found: {norm}")
            link = _link_info(parent, name)
            obj = _resolve(parent, name)
        node: dict[str, Any] = {"path": norm, "name": name, "link": link, "broken": obj is None}
        if obj is None:
            node["kind"] = "link"
            node["attributes"] = []
            node["error"] = "Link target cannot be opened (broken or missing external file)."
            return node
        node["attributes"] = _read_attributes(obj, hf)
        if isinstance(obj, h5py.Group):
            node.update(kind="group", members=len(obj))
        elif isinstance(obj, h5py.Dataset):
            node.update(kind="dataset", **_dataset_details(obj, hf))
        else:
            node.update(kind="datatype", dtype=_describe_dtype(obj.dtype))
        return node


def _clamp(value: Any, low: int, high: int) -> int:
    # Clamp a possibly invalid integer into a closed range.
    try:
        num = int(value)
    except (TypeError, ValueError):
        num = low
    return max(low, min(num, high))


def _numeric_stats(ds: Any, window: Any) -> dict[str, Any] | None:
    # Compute min, max, mean, and std for numeric datasets.
    desc = _describe_dtype(ds.dtype)
    if desc["kind"] not in ("integer", "unsigned", "float"):
        return None
    whole = ds.size <= MAX_STAT_ELEMENTS
    data = np.asarray(ds[()] if whole else window)
    if data.size == 0:
        return None
    nan_count = 0
    if data.dtype.kind == "f":
        mask = np.isfinite(data)
        nan_count = int(np.isnan(data).sum())
        data = data[mask]
    stats: dict[str, Any] = {"scope": "dataset" if whole else "window", "count": int(data.size), "nan_count": nan_count}
    if data.size == 0:
        stats.update(min=None, max=None, mean=None, std=None)
        return stats
    stats.update(
        min=_json_value(data.min()),
        max=_json_value(data.max()),
        mean=_json_value(float(np.mean(data, dtype=np.float64))),
        std=_json_value(float(np.std(data, dtype=np.float64))),
    )
    return stats


def _window_rows(window: Any, desc: dict[str, Any], hf: Any, col_names: list[str] | None) -> list[list[Any]]:
    # Turn a sliced array into a list of display rows.
    enum_rev = {member: name for name, member in desc.get("enum", {}).items()}

    def cell(value: Any) -> Any:
        out = _json_value(value, hf)
        if enum_rev and isinstance(out, int):
            return enum_rev.get(out, out)
        return out

    arr = np.asarray(window)
    if col_names is not None:
        return [[cell(row[name]) for name in col_names] for row in arr]
    if arr.ndim == 0:
        return [[cell(arr[()])]]
    if arr.ndim == 1:
        return [[cell(item)] for item in arr]
    return [[cell(item) for item in row] for row in arr]


def preview_hdf5_dataset(
    file_path: str,
    path: str,
    row_start: int = 0,
    row_count: int = 20,
    col_start: int = 0,
    col_count: int = 12,
    index: list[int] | None = None,
    include_stats: bool = True,
) -> dict[str, Any]:
    # Read a bounded row and column window of a dataset with optional statistics.
    norm = _norm_path(path)
    with _open_file(file_path) as hf:
        ds = _get_dataset(hf, norm)
        desc = _describe_dtype(ds.dtype)
        result: dict[str, Any] = {"path": norm, "shape": list(ds.shape) if ds.shape is not None else None, "dtype": desc["label"], "kind": desc["kind"]}
        if ds.shape is None or ds.size == 0:
            result.update(columns=[], rows=[], row_start=0, row_count=0, col_start=0, col_count=0, total_rows=0, total_cols=0, leading_index=[], slice_spec=":", stats=None, empty=True)
            return result
        shape = tuple(int(n) for n in ds.shape)
        ndim = len(shape)
        fields = desc.get("fields", []) if ds.dtype.names else []
        leading: list[int] = []
        if ndim >= 3:
            wanted = list(index or [])
            for axis in range(ndim - 2):
                leading.append(_clamp(wanted[axis] if axis < len(wanted) else 0, 0, shape[axis] - 1))
        if ndim == 0:
            total_rows, total_cols = 1, 1
        elif ndim == 1:
            total_rows, total_cols = shape[0], (len(fields) if fields else 1)
        else:
            total_rows, total_cols = shape[-2], shape[-1]
        rows_n = _clamp(row_count, 1, MAX_PREVIEW_ROWS)
        cols_n = _clamp(col_count, 1, min(MAX_PREVIEW_COLS, max(1, MAX_PREVIEW_CELLS // rows_n)))
        r0 = _clamp(row_start, 0, max(total_rows - 1, 0))
        r1 = min(total_rows, r0 + rows_n)
        c0 = _clamp(col_start, 0, max(total_cols - 1, 0))
        c1 = min(total_cols, c0 + cols_n)
        col_names: list[str] | None = None
        if ndim == 0:
            selection: tuple[Any, ...] = ()
            columns = ["value"]
            spec = ":"
        elif ndim == 1:
            selection = (slice(r0, r1),)
            spec = f"{r0}:{r1}"
            if fields:
                col_names = [f["name"] for f in fields][c0:c1]
                columns = list(col_names)
            else:
                columns = ["value"]
        else:
            selection = tuple(leading) + (slice(r0, r1), slice(c0, c1))
            spec = ",".join([str(i) for i in leading] + [f"{r0}:{r1}", f"{c0}:{c1}"])
            columns = [str(n) for n in range(c0, c1)]
        window = ds[selection]
        rows = _window_rows(window, desc, hf, col_names)
        stats = _numeric_stats(ds, window) if include_stats else None
        result.update(
            columns=columns,
            rows=rows,
            row_start=r0,
            row_count=len(rows),
            col_start=c0,
            col_count=len(columns),
            total_rows=total_rows,
            total_cols=total_cols,
            leading_index=leading,
            slice_spec=spec,
            stats=stats,
            empty=False,
        )
        return result


def search_hdf5(file_path: str, query: str, limit: int = 200) -> dict[str, Any]:
    import h5py
            # Find members whose path contains the query text.
    needle = str(query or "").strip().lower()
    cap = max(1, min(int(limit), 1000))
    matches: list[dict[str, Any]] = []
    truncated = False
    visits = 0
    if not needle:
        return {"query": needle, "matches": matches, "truncated": False, "visited": 0}
    with _open_file(file_path) as hf:
        root = hf["/"]
        visited_ids = {root.id}
        pending: deque[tuple[str, Any]] = deque([("/", root)])
        while pending and not truncated:
            parent_path, grp = pending.popleft()
            for name in grp:
                visits += 1
                if visits > MAX_SEARCH_VISITS:
                    truncated = True
                    break
                obj = _resolve(grp, name)
                link = _link_info(grp, name)
                child_path = _join_path(parent_path, name)
                if needle in child_path.lower():
                    matches.append(_summarize(parent_path, name, obj, link))
                    if len(matches) >= cap:
                        truncated = True
                        break
                if isinstance(obj, h5py.Group) and link["type"] == "hard" and obj.id not in visited_ids:
                    visited_ids.add(obj.id)
                    pending.append((child_path, obj))
    return {"query": needle, "matches": matches, "truncated": truncated, "visited": visits}


def _inline_preview(ds: Any) -> Any:
    # Return a short value preview for tree summaries.
    try:
        if ds.shape is None or ds.size == 0:
            return "[]"
        if ds.ndim == 0:
            return _json_value(ds[()])
        if ds.ndim == 1:
            shown = min(10, ds.shape[0])
            values = _json_value(ds[:shown])
            if ds.shape[0] > shown:
                values.append(f"... (+{ds.shape[0] - shown} more)")
            return values
    except H5_ERRORS:
        return None
    return None


def inspect_hdf5(file_path: str) -> dict[str, Any]:
    import h5py
            # Walk the file into a bounded hierarchical tree for generic structure views.
    counts = {"groups": 0, "datasets": 0, "attributes": 0, "nodes": 0}
    truncated = False

    def attr_map(obj: Any, hf: Any) -> dict[str, str]:
        out: dict[str, str] = {}
        for item in _read_attributes(obj, hf):
            counts["attributes"] += 1
            out[item["name"]] = str(item.get("value", item.get("error", "")))[:200]
        return out

    def walk(grp: Any, name: str, path: str, hf: Any, seen: set[Any]) -> dict[str, Any]:
        nonlocal truncated
        counts["groups"] += 1
        counts["nodes"] += 1
        children: list[dict[str, Any]] = []
        for key in grp:
            if counts["nodes"] >= MAX_TREE_NODES:
                truncated = True
                break
            obj = _resolve(grp, key)
            link = _link_info(grp, key)
            child_path = _join_path(path, key)
            if obj is None or link["type"] != "hard":
                counts["nodes"] += 1
                note = "broken link" if obj is None else "link"
                children.append({"name": key, "type": "link", "path": child_path, "attributes": {}, "children": [], "preview": f"{note} -> {link.get('target', '')}"})
            elif isinstance(obj, h5py.Group):
                if obj.id in seen:
                    continue
                seen.add(obj.id)
                children.append(walk(obj, key, child_path, hf, seen))
            elif isinstance(obj, h5py.Dataset):
                counts["datasets"] += 1
                counts["nodes"] += 1
                children.append({
                    "name": key,
                    "type": "dataset",
                    "path": child_path,
                    "shape": list(obj.shape) if obj.shape is not None else None,
                    "dtype": _describe_dtype(obj.dtype)["label"],
                    "size_bytes": int(obj.nbytes) if obj.size is not None else 0,
                    "chunks": list(obj.chunks) if obj.chunks else None,
                    "compression": obj.compression,
                    "attributes": attr_map(obj, hf),
                    "preview": _inline_preview(obj),
                    "children": [],
                })
        return {"name": name, "type": "group", "path": path, "attributes": attr_map(grp, hf), "children": children, "count": len(children)}

    with _open_file(file_path) as hf:
        root_group = hf["/"]
        root = walk(root_group, "/", "/", hf, {root_group.id})
    return {
        "format": "HDF5",
        "backend": "h5py",
        "file_path": file_path,
        "file_size": os.path.getsize(file_path),
        "root": root,
        "summary": {
            "groups_count": counts["groups"],
            "datasets_count": counts["datasets"],
            "attributes_count": counts["attributes"],
            "truncated": truncated,
        },
    }


def _parse_slice_spec(slice_spec: str, shape: tuple[int, ...]) -> tuple[Any, ...]:
    # Parse a comma separated slice expression into indexers.
    clean = str(slice_spec or "").strip()
    if not clean or clean in (":", "all"):
        return tuple(slice(None) for _ in shape)
    parts = clean.split(",")
    if len(parts) > len(shape):
        raise Hdf5Error(f"Slice has {len(parts)} indexes but dataset has {len(shape)} dimensions")
    res: list[Any] = []
    for part in parts:
        token = part.strip()
        try:
            if ":" in token:
                bits = [bit.strip() for bit in token.split(":")]
                if len(bits) > 3:
                    raise ValueError(token)
                nums = [int(bit) if bit else None for bit in bits]
                res.append(slice(*nums))
            else:
                res.append(int(token))
        except ValueError as exc:
            raise Hdf5Error(f"Invalid slice index: '{token}'") from exc
    while len(res) < len(shape):
        res.append(slice(None))
    return tuple(res)


def _selection_count(selection: tuple[Any, ...], shape: tuple[int, ...]) -> int:
    # Count the elements a selection will read.
    total = 1
    for indexer, size in zip(selection, shape):
        total *= len(range(*indexer.indices(size))) if isinstance(indexer, slice) else 1
    return total


def _csv_cell(value: Any, hf: Any) -> Any:
    # Format one array element for CSV output.
    out = _json_value(value, hf)
    return json.dumps(out) if isinstance(out, (dict, list)) else out


def _write_array_to_csv(arr: np.ndarray, output_path: str, hf: Any) -> None:
    # Save an array as CSV with a header row for compound data.
    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if arr.dtype.names and arr.ndim == 1:
            writer.writerow(list(arr.dtype.names))
            for row in arr:
                writer.writerow([_csv_cell(row[name], hf) for name in arr.dtype.names])
        elif arr.ndim == 0:
            writer.writerow([_csv_cell(arr[()], hf)])
        elif arr.ndim == 1:
            for item in arr:
                writer.writerow([_csv_cell(item, hf)])
        else:
            for row in arr.reshape(-1, arr.shape[-1]):
                writer.writerow([_csv_cell(item, hf) for item in row])


def export_hdf5_slice(
    file_path: str,
    dataset_path: str,
    slice_spec: str,
    output_path: str,
    out_format: str = "csv",
) -> dict[str, Any]:
    # Export a bounded dataset slice to CSV, JSON, or NPY.
    fmt = str(out_format).lower().strip()
    if fmt not in ("csv", "json", "npy"):
        raise Hdf5Error(f"Unsupported export format: {out_format}")
    with _open_file(file_path) as hf:
        ds = _get_dataset(hf, _norm_path(dataset_path))
        shape = tuple(int(n) for n in ds.shape) if ds.shape is not None else ()
        selection = _parse_slice_spec(slice_spec, shape)
        if _selection_count(selection, shape) > MAX_EXPORT_ELEMENTS:
            raise Hdf5Error(f"Slice exceeds {MAX_EXPORT_ELEMENTS} elements; narrow the slice before exporting")
        arr = np.asarray(ds[selection])
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        if fmt == "npy":
            if arr.dtype.hasobject:
                raise Hdf5Error("NPY export does not support object or variable-length data; use CSV or JSON")
            np.save(output_path, arr)
        elif fmt == "json":
            with open(output_path, "w", encoding="utf-8") as handle:
                json.dump(_json_value(arr, hf), handle, indent=2)
        else:
            _write_array_to_csv(arr, output_path, hf)
        return {
            "output_path": output_path,
            "format": fmt.upper(),
            "shape": list(arr.shape),
            "size": int(arr.size),
            "dtype": str(arr.dtype),
        }
