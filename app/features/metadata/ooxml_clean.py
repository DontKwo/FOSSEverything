"""Sanitize Office Open XML packages (docx, xlsx, pptx and macro variants) of author data, comments, and revisions."""

from __future__ import annotations

import os
import posixpath
import re
import zipfile
from typing import Any

from lxml import etree

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS_SS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
NS_DC = "http://purl.org/dc/elements/1.1/"
NS_DCTERMS = "http://purl.org/dc/terms/"
NS_EP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"

OOXML_EXTENSIONS = {".docx", ".xlsx", ".pptx", ".docm", ".xlsm", ".pptm"}

_REMOVED_PART_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"word/(comments|commentsExtended|commentsIds|commentsExtensible|people)\.xml",
        r"xl/comments(/.+|\d*\.xml)",
        r"xl/threadedComments/.+",
        r"xl/persons/.+",
        r"xl/revisions/.+",
        r"ppt/comments/.+",
        r"ppt/commentAuthors\.xml",
        r"ppt/authors\.xml",
        r"docProps/custom\.xml",
    )
)
_WORD_CONTENT_PART = re.compile(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml")
_COMMENT_PART = re.compile(r"(word/comments\.xml|xl/comments(/.+|\d*\.xml)|xl/threadedComments/.+|ppt/comments/.+)")
_TRACKED_TAG = re.compile(rb"<w:(ins|del|moveFrom|moveTo)[ >/]")

_REMOVE_TAGS = (
    "del",
    "moveFrom",
    "rPrChange",
    "pPrChange",
    "sectPrChange",
    "tblPrChange",
    "tblGridChange",
    "trPrChange",
    "tcPrChange",
    "tblPrExChange",
    "numberingChange",
    "cellDel",
    "cellIns",
    "cellMerge",
    "moveFromRangeStart",
    "moveFromRangeEnd",
    "moveToRangeStart",
    "moveToRangeEnd",
    "commentRangeStart",
    "commentRangeEnd",
)
_UNWRAP_TAGS = ("ins", "moveTo")

BLANK_CORE_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    f'<cp:coreProperties xmlns:cp="{NS_CP}" xmlns:dc="{NS_DC}" xmlns:dcterms="{NS_DCTERMS}">'
    "<dc:title></dc:title><dc:creator></dc:creator><cp:lastModifiedBy></cp:lastModifiedBy>"
    "<cp:revision>1</cp:revision></cp:coreProperties>"
)
BLANK_APP_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    f'<Properties xmlns="{NS_EP}"><Application>FOSSEverything</Application><Company></Company></Properties>'
)


_PARSER = etree.XMLParser(resolve_entities=False, no_network=True)


def _parse(data: bytes) -> Any:
    return etree.fromstring(data, _PARSER)


def _is_removed_part(name: str) -> bool:
    return any(pattern.fullmatch(name) for pattern in _REMOVED_PART_PATTERNS)


def _serialize(root: Any) -> bytes:
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def _resolve_target(rels_name: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    source_dir = posixpath.dirname(posixpath.dirname(rels_name))
    return posixpath.normpath(posixpath.join(source_dir, target))


def _rels_source_part(rels_name: str) -> str:
    source_dir = posixpath.dirname(posixpath.dirname(rels_name))
    base = posixpath.basename(rels_name)[: -len(".rels")]
    return posixpath.join(source_dir, base) if base else ""


def count_tracked_changes(xml_bytes: bytes) -> int:
    """Count tracked insertion, deletion, and move markers in WordprocessingML bytes."""
    return len(_TRACKED_TAG.findall(xml_bytes))


def accept_tracked_changes(root: Any) -> int:
    """Accept all revisions and drop comment anchors in a WordprocessingML tree; returns elements changed."""
    changed = 0
    prefix = "{" + NS_W + "}"
    for tag in _REMOVE_TAGS:
        for element in list(root.iter(prefix + tag)):
            parent = element.getparent()
            if parent is None:
                continue
            parent.remove(element)
            changed += 1
    for reference in list(root.iter(prefix + "commentReference")):
        run = reference.getparent()
        if run is not None and run.getparent() is not None:
            run.getparent().remove(run)
            changed += 1
    for tag in _UNWRAP_TAGS:
        for element in list(root.iter(prefix + tag)):
            parent = element.getparent()
            if parent is None:
                continue
            if parent.tag in (prefix + "rPr", prefix + "trPr"):
                parent.remove(element)
                changed += 1
                continue
            position = parent.index(element)
            for child in list(element):
                parent.insert(position, child)
                position += 1
            parent.remove(element)
            changed += 1
    return changed


def _clean_rels(rels_name: str, data: bytes, removed: set[str], vml_to_drop: set[str]) -> bytes:
    root = _parse(data)
    for rel in list(root):
        if rel.get("TargetMode") == "External":
            continue
        target = _resolve_target(rels_name, rel.get("Target", ""))
        if target in removed or target in vml_to_drop:
            root.remove(rel)
    return _serialize(root)


def _clean_content_types(data: bytes, removed: set[str]) -> bytes:
    root = _parse(data)
    for override in list(root):
        part_name = override.get("PartName", "").lstrip("/")
        if override.tag == "{" + NS_CT + "}Override" and part_name in removed:
            root.remove(override)
    return _serialize(root)


def _find_comment_vml_parts(archive: zipfile.ZipFile, removed: set[str]) -> tuple[set[str], set[str]]:
    # Comment shapes live in vmlDrawing parts referenced by the same sheet as the comments part.
    vml_parts: set[str] = set()
    sheets: set[str] = set()
    for name in archive.namelist():
        if not name.endswith(".rels"):
            continue
        root = _parse(archive.read(name))
        rels = [(rel.get("Type", ""), _resolve_target(name, rel.get("Target", ""))) for rel in root]
        if not any(target in removed and _COMMENT_PART.fullmatch(target) for _, target in rels):
            continue
        for rel_type, target in rels:
            if rel_type.endswith("/vmlDrawing"):
                vml_parts.add(target)
                sheets.add(_rels_source_part(name))
    return vml_parts, sheets


def _clean_sheet(data: bytes) -> bytes:
    root = _parse(data)
    for element in list(root.iter("{" + NS_SS + "}legacyDrawing")):  # noqa: 8
        element.getparent().remove(element)
    return _serialize(root)


def _clean_workbook(data: bytes) -> bytes:
    root = _parse(data)
    for element in list(root.iter("{" + NS_SS + "}fileSharing")):
        element.getparent().remove(element)
    return _serialize(root)


def _clean_word_settings(data: bytes) -> bytes:
    root = _parse(data)
    for tag in ("trackRevisions", "revisionView"):
        for element in list(root.iter("{" + NS_W + "}" + tag)):
            element.getparent().remove(element)
    return _serialize(root)


def sanitize_ooxml(input_path: str, output_path: str) -> dict[str, int]:
    """Write a sanitized copy of an OOXML package and return counts of what was removed."""
    stats = {"parts_removed": 0, "tracked_changes_accepted": 0}
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with zipfile.ZipFile(input_path, "r") as zin:
        names = zin.namelist()
        removed = {name for name in names if _is_removed_part(name)}
        vml_parts, flagged_sheets = _find_comment_vml_parts(zin, removed)
        removed_all = removed | vml_parts
        stats["parts_removed"] = len(removed_all)
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                name = item.filename
                if name in removed_all:
                    continue
                if name.endswith(".rels") and _rels_source_part(name) in removed_all:
                    continue
                data = zin.read(name)
                if name == "docProps/core.xml":
                    data = BLANK_CORE_XML.encode("utf-8")
                elif name == "docProps/app.xml":
                    data = BLANK_APP_XML.encode("utf-8")
                elif name == "[Content_Types].xml":
                    data = _clean_content_types(data, removed_all)
                elif name.endswith(".rels"):
                    data = _clean_rels(name, data, removed, vml_parts)
                elif _WORD_CONTENT_PART.fullmatch(name):
                    root = _parse(data)
                    stats["tracked_changes_accepted"] += accept_tracked_changes(root)
                    data = _serialize(root)
                elif name == "word/settings.xml":
                    data = _clean_word_settings(data)
                elif name == "xl/workbook.xml":
                    data = _clean_workbook(data)
                elif name in flagged_sheets:
                    data = _clean_sheet(data)
                zout.writestr(item, data)
    return stats


def ooxml_review_counts(path: str) -> dict[str, int]:
    """Count comment parts and tracked changes present in an OOXML package."""
    comment_parts = 0
    tracked = 0
    with zipfile.ZipFile(path, "r") as archive:
        for name in archive.namelist():
            if _COMMENT_PART.fullmatch(name):
                comment_parts += 1
            elif _WORD_CONTENT_PART.fullmatch(name):
                tracked += count_tracked_changes(archive.read(name))
            elif name.startswith("xl/revisions/") and name.endswith(".xml"):
                tracked += 1
    return {"comment_parts": comment_parts, "tracked_changes": tracked}
