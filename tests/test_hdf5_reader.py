import csv
import json
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import pytest

from app.web.api import WebApi
from app.web.api.hdf5_reader import (
    Hdf5Error,
    describe_hdf5_node,
    export_hdf5_slice,
    inspect_hdf5,
    is_hdf5_file,
    list_hdf5_children,
    open_hdf5,
    preview_hdf5_dataset,
    search_hdf5,
)


@pytest.fixture()
def h5_path(tmp_path: Path) -> str:
    # Build an HDF5 file covering compound, enum, vlen, links, attrs, and chunked data.
    path = tmp_path / "viewer.h5"
    with h5py.File(path, "w") as hf:
        hf.attrs["title"] = "viewer test"
        hf.attrs["raw"] = np.bytes_(b"bytes-attr")
        hf.attrs["vector"] = np.arange(5, dtype=np.int16)
        grp = hf.create_group("group_a")
        grp.attrs["note"] = "group note"
        compound = np.dtype([("id", "i4"), ("score", "f8"), ("tag", "S4")])
        rec = np.array([(1, 0.5, b"aa"), (2, 1.5, b"bb"), (3, 2.5, b"cc")], dtype=compound)
        grp.create_dataset("records", data=rec)
        enum_dt = h5py.enum_dtype({"RED": 0, "GREEN": 1, "BLUE": 2}, basetype="i1")
        grp.create_dataset("colors", data=np.array([0, 2, 1, 1], dtype="i1"), dtype=enum_dt)
        grp.create_dataset("names", data=["alpha", "beta", "gamma"], dtype=h5py.string_dtype())
        grp.create_dataset("flags", data=np.array([True, False, True]))
        grp.create_dataset("cplx", data=np.array([1 + 2j, 3 - 4j]))
        big = np.arange(60 * 40, dtype="f8").reshape(60, 40)
        grp.create_dataset("grid", data=big, chunks=(10, 10), compression="gzip", compression_opts=4, shuffle=True, maxshape=(None, 40), fillvalue=-1.0)
        grp.create_dataset("cube", data=np.arange(24, dtype="i4").reshape(2, 3, 4))
        grp.create_dataset("scalar", data=7)
        grp.create_dataset("nan_values", data=np.array([1.0, np.nan, 3.0]))
        hf.create_dataset("refs", data=[grp["records"].ref, grp["grid"].ref], dtype=h5py.ref_dtype)
        hf["soft_ok"] = h5py.SoftLink("/group_a/grid")
        hf["soft_broken"] = h5py.SoftLink("/missing/target")
        hf["external"] = h5py.ExternalLink("does_not_exist.h5", "/data")
        hf["hard_alias"] = grp["scalar"]
    return str(path)


def test_open_lists_root_members_and_file_attrs(h5_path: str) -> None:
    info = open_hdf5(h5_path)
    names = [child["name"] for child in info["root"]["children"]]
    assert {"group_a", "refs", "soft_ok", "soft_broken", "external", "hard_alias"} <= set(names)
    attrs = {a["name"]: a for a in info["attributes"]}
    assert attrs["title"]["value"] == "viewer test"
    assert attrs["raw"]["value"] == "bytes-attr"
    assert attrs["vector"]["value"] == [0, 1, 2, 3, 4]
    assert attrs["vector"]["shape"] == [5]


def test_children_paging_and_link_kinds(h5_path: str) -> None:
    page = list_hdf5_children(h5_path, "/", offset=0, limit=2)
    assert len(page["children"]) == 2
    assert page["has_more"] is True
    everything = {c["name"]: c for c in list_hdf5_children(h5_path, "/")["children"]}
    assert everything["soft_ok"]["link"] == {"type": "soft", "target": "/group_a/grid"}
    assert everything["soft_ok"]["kind"] == "dataset"
    assert everything["soft_broken"]["broken"] is True
    assert everything["soft_broken"]["kind"] == "link"
    assert everything["external"]["link"]["type"] == "external"
    assert everything["external"]["link"]["filename"] == "does_not_exist.h5"
    assert everything["external"]["broken"] is True
    assert everything["hard_alias"]["link"]["type"] == "hard"
    assert everything["group_a"]["members"] == 9


def test_chunked_compressed_dataset_details(h5_path: str) -> None:
    node = describe_hdf5_node(h5_path, "/group_a/grid")
    assert node["kind"] == "dataset"
    assert node["shape"] == [60, 40]
    assert node["maxshape"] == ["unlimited", 40]
    assert node["layout"] == "chunked"
    assert node["chunks"] == [10, 10]
    assert node["compression"] == "gzip"
    assert node["compression_opts"] == 4
    assert node["shuffle"] is True
    assert node["fillvalue"] == -1.0
    assert node["nbytes"] == 60 * 40 * 8
    assert node["storage_bytes"] > 0
    assert any(f["name"] for f in node["filters"])


def test_compound_enum_vlen_bool_complex_details(h5_path: str) -> None:
    rec = describe_hdf5_node(h5_path, "/group_a/records")
    assert rec["dtype"]["kind"] == "compound"
    assert [f["name"] for f in rec["fields"]] == ["id", "score", "tag"]
    enum = describe_hdf5_node(h5_path, "/group_a/colors")
    assert enum["dtype"]["kind"] == "enum"
    assert enum["dtype"]["enum"] == {"RED": 0, "GREEN": 1, "BLUE": 2}
    assert describe_hdf5_node(h5_path, "/group_a/names")["dtype"]["kind"] == "vlen_string"
    assert describe_hdf5_node(h5_path, "/group_a/flags")["dtype"]["kind"] == "bool"
    assert describe_hdf5_node(h5_path, "/group_a/cplx")["dtype"]["kind"] == "complex"
    assert describe_hdf5_node(h5_path, "/refs")["dtype"]["kind"] == "reference"


def test_group_attributes_and_hard_link(h5_path: str) -> None:
    node = describe_hdf5_node(h5_path, "/group_a")
    assert node["kind"] == "group"
    assert node["attributes"][0]["value"] == "group note"
    alias = describe_hdf5_node(h5_path, "/hard_alias")
    assert alias["link"]["type"] == "hard"
    assert alias["kind"] == "dataset"


def test_broken_and_missing_nodes(h5_path: str) -> None:
    broken = describe_hdf5_node(h5_path, "/soft_broken")
    assert broken["broken"] is True
    assert broken["link"]["target"] == "/missing/target"
    assert "error" in broken
    with pytest.raises(Hdf5Error):
        describe_hdf5_node(h5_path, "/nope/nothing")


def test_preview_window_matches_numpy_slice(h5_path: str) -> None:
    res = preview_hdf5_dataset(h5_path, "/group_a/grid", row_start=10, row_count=4, col_start=5, col_count=3)
    expected = np.arange(60 * 40, dtype="f8").reshape(60, 40)[10:14, 5:8]
    assert res["rows"] == expected.tolist()
    assert res["columns"] == ["5", "6", "7"]
    assert res["total_rows"] == 60
    assert res["total_cols"] == 40
    assert res["slice_spec"] == "10:14,5:8"
    assert res["stats"]["scope"] == "dataset"
    assert res["stats"]["min"] == 0.0
    assert res["stats"]["max"] == 2399.0
    assert res["stats"]["mean"] == pytest.approx(1199.5)


def test_preview_is_bounded(h5_path: str) -> None:
    res = preview_hdf5_dataset(h5_path, "/group_a/grid", row_start=0, row_count=100000, col_count=100000)
    assert res["row_count"] <= 60
    assert res["col_count"] <= 40
    far = preview_hdf5_dataset(h5_path, "/group_a/grid", row_start=9999, row_count=5)
    assert far["row_start"] == 59
    assert far["row_count"] == 1


def test_preview_three_dimensional_leading_index(h5_path: str) -> None:
    res = preview_hdf5_dataset(h5_path, "/group_a/cube", index=[1])
    assert res["leading_index"] == [1]
    assert res["rows"] == np.arange(24).reshape(2, 3, 4)[1].tolist()
    assert res["slice_spec"].startswith("1,")


def test_preview_compound_enum_strings_refs_complex(h5_path: str) -> None:
    rec = preview_hdf5_dataset(h5_path, "/group_a/records")
    assert rec["columns"] == ["id", "score", "tag"]
    assert rec["rows"][1] == [2, 1.5, "bb"]
    assert rec["stats"] is None
    enum = preview_hdf5_dataset(h5_path, "/group_a/colors")
    assert [r[0] for r in enum["rows"]] == ["RED", "BLUE", "GREEN", "GREEN"]
    names = preview_hdf5_dataset(h5_path, "/group_a/names")
    assert [r[0] for r in names["rows"]] == ["alpha", "beta", "gamma"]
    flags = preview_hdf5_dataset(h5_path, "/group_a/flags")
    assert [r[0] for r in flags["rows"]] == [True, False, True]
    cplx = preview_hdf5_dataset(h5_path, "/group_a/cplx")
    assert cplx["rows"][0][0] == "1+2j"
    refs = preview_hdf5_dataset(h5_path, "/refs")
    assert [r[0] for r in refs["rows"]] == ["ref:/group_a/records", "ref:/group_a/grid"]
    scalar = preview_hdf5_dataset(h5_path, "/group_a/scalar")
    assert scalar["rows"] == [[7]]


def test_stats_ignore_nan_and_can_be_skipped(h5_path: str) -> None:
    res = preview_hdf5_dataset(h5_path, "/group_a/nan_values")
    assert res["stats"]["nan_count"] == 1
    assert res["stats"]["min"] == 1.0
    assert res["stats"]["max"] == 3.0
    assert preview_hdf5_dataset(h5_path, "/group_a/nan_values", include_stats=False)["stats"] is None


def test_search_matches_paths_and_follows_only_hard_groups(h5_path: str) -> None:
    res = search_hdf5(h5_path, "GRID")
    paths = {m["path"] for m in res["matches"]}
    assert "/group_a/grid" in paths
    assert "/soft_ok" not in paths
    assert search_hdf5(h5_path, "soft")["matches"]
    assert search_hdf5(h5_path, "")["matches"] == []
    assert search_hdf5(h5_path, "a", limit=2)["truncated"] is True


def test_export_slice_csv_json_and_compound(h5_path: str, tmp_path: Path) -> None:
    out_csv = tmp_path / "slice.csv"
    res = export_hdf5_slice(h5_path, "/group_a/grid", "0:2,0:3", str(out_csv), "csv")
    assert res["shape"] == [2, 3]
    rows = list(csv.reader(out_csv.read_text(encoding="utf-8").splitlines()))
    assert rows == [["0.0", "1.0", "2.0"], ["40.0", "41.0", "42.0"]]
    out_json = tmp_path / "slice.json"
    export_hdf5_slice(h5_path, "/group_a/grid", "1,0:2", str(out_json), "json")
    assert json.loads(out_json.read_text(encoding="utf-8")) == [40.0, 41.0]
    out_rec = tmp_path / "rec.csv"
    export_hdf5_slice(h5_path, "/group_a/records", ":", str(out_rec), "csv")
    lines = out_rec.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "id,score,tag"
    assert lines[1] == "1,0.5,aa"


def test_export_rejects_bad_input(h5_path: str, tmp_path: Path) -> None:
    out = str(tmp_path / "x.csv")
    with pytest.raises(Hdf5Error):
        export_hdf5_slice(h5_path, "/group_a/grid", "abc", out, "csv")
    with pytest.raises(Hdf5Error):
        export_hdf5_slice(h5_path, "/group_a/grid", "0,0,0", out, "csv")
    with pytest.raises(Hdf5Error):
        export_hdf5_slice(h5_path, "/group_a/grid", ":", out, "xlsx")
    with pytest.raises(Hdf5Error):
        export_hdf5_slice(h5_path, "/group_a", ":", out, "csv")


def test_inspect_tree_is_bounded_and_marks_links(h5_path: str) -> None:
    tree = inspect_hdf5(h5_path)
    assert tree["format"] == "HDF5"
    assert tree["summary"]["datasets_count"] >= 10
    child_types = {c["name"]: c["type"] for c in tree["root"]["children"]}
    assert child_types["soft_broken"] == "link"
    assert child_types["group_a"] == "group"


def test_corrupt_and_non_hdf5_inputs(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.h5"
    corrupt.write_bytes(b"\x89HDF\r\n\x1a\n" + b"\x00" * 56)
    plain = tmp_path / "plain.h5"
    plain.write_text("not hdf5 at all", encoding="utf-8")
    for bad in (str(corrupt), str(plain), str(tmp_path / "missing.h5")):
        with pytest.raises(Hdf5Error):
            open_hdf5(bad)
        with pytest.raises(Hdf5Error):
            inspect_hdf5(bad)
    assert is_hdf5_file(str(plain)) is False


def test_api_methods_return_clean_dicts(h5_path: str, tmp_path: Path) -> None:
    api = WebApi()
    for name in ("data_hdf5_open", "data_hdf5_children", "data_hdf5_node", "data_hdf5_preview", "data_hdf5_search", "data_hdf5_export_slice"):
        res = getattr(api, name)({})
        assert res["ok"] is False
    opened = api.data_hdf5_open({"file_path": h5_path})
    assert opened["ok"] is True
    kids: dict[str, Any] = api.data_hdf5_children({"file_path": h5_path, "path": "/group_a"})
    assert kids["ok"] and kids["total"] == 9
    assert api.data_hdf5_node({"file_path": h5_path, "path": "/group_a/grid"})["layout"] == "chunked"
    prev = api.data_hdf5_preview({"file_path": h5_path, "path": "/group_a/grid", "row_count": 2, "col_count": 2})
    assert prev["ok"] and len(prev["rows"]) == 2
    assert api.data_hdf5_search({"file_path": h5_path, "query": "cube"})["matches"][0]["path"] == "/group_a/cube"
    out = tmp_path / "api.json"
    exp = api.data_hdf5_export_slice({"file_path": h5_path, "dataset_path": "/group_a/cube", "slice_spec": "0", "output_path": str(out), "format": "json"})
    assert exp["ok"] is True
    assert json.loads(out.read_text(encoding="utf-8"))[0] == [0, 1, 2, 3]
    corrupt = tmp_path / "bad.h5"
    corrupt.write_bytes(b"\x89HDF\r\n\x1a\n" + b"\x00" * 56)
    bad = api.data_hdf5_open({"file_path": str(corrupt)})
    assert bad["ok"] is False
    assert bad["code"] == "Hdf5Error"
    assert api.data_inspect_structure({"file_path": str(corrupt)})["ok"] is False


def test_repository_sample_files() -> None:
    sample = Path("tests/test_data/sample.h5")
    if not sample.exists():
        pytest.skip("sample.h5 not generated")
    info = open_hdf5(str(sample))
    assert {c["name"] for c in info["root"]["children"]} >= {"telemetry", "navigation", "config"}
    prev = preview_hdf5_dataset(str(sample), "/telemetry/accelerometer", row_count=5, col_count=3)
    assert prev["total_rows"] == 100
    assert prev["total_cols"] == 3
