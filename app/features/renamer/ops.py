"""Headless batch file renaming engine with regex, numbering, and collision safety."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from PIL import Image
from mutagen import File as MutagenFile


@dataclass
class RenamePlan:
    old_path: str
    old_name: str
    new_name: str
    new_path: str
    error: str | None = None
    has_collision: bool = False


@dataclass
class RenameResult:
    old_path: str
    new_path: str
    success: bool
    error: str | None = None


def save_preset(name: str, mode: str, params: dict) -> dict:
    """Create a serializable rename preset object for a single saved rule set."""
    clean_name = (name or "untitled").strip()
    if not clean_name:
        raise ValueError("Preset name cannot be empty.")
    return {
        "name": clean_name,
        "mode": mode,
        "params": params or {},
    }


def undo_renames(changes: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Return a reverse rename list suitable for undoing a completed rename session."""
    return [(new_path, old_path) for old_path, new_path in changes]


def apply_case_transform(text: str, case_type: str) -> str:
    """Apply uppercase, lowercase, title case, or sentence case."""
    c = case_type.lower()
    if c == "upper":
        return text.upper()
    elif c == "lower":
        return text.lower()
    elif c == "title":
        return text.title()
    elif c == "sentence":
        return text.capitalize()
    return text


def _sanitize_token(value: str | None) -> str:
    """Convert metadata values into a filename-safe token value."""
    if value is None:
        return "unknown"
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("._")
    return cleaned or "unknown"


def extract_rename_metadata(file_path: str) -> dict[str, str]:
    """Extract EXIF and ID3 metadata available for filename templates."""
    base_name = os.path.basename(file_path)
    stem, ext = os.path.splitext(base_name)
    modified = datetime.fromtimestamp(os.path.getmtime(file_path))
    metadata: dict[str, str] = {
        "name": stem,
        "stem": stem,
        "filename": base_name,
        "original": base_name,
        "extension": ext.lstrip("."),
        "ext": ext,
        "date": modified.strftime("%Y-%m-%d"),
        "datetime": modified.strftime("%Y-%m-%d %H:%M:%S"),
        "year": modified.strftime("%Y"),
        "month": modified.strftime("%m"),
        "day": modified.strftime("%d"),
        "time": modified.strftime("%H-%M-%S"),
        "camera": "unknown",
        "artist": "unknown",
        "album": "unknown",
        "title": stem,
    }

    lower_ext = ext.lower()
    try:
        if lower_ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}:
            with Image.open(file_path) as image:
                exif = image.getexif()
                for key in (36867, 306, 36868):
                    value = exif.get(key)
                    if value:
                        metadata["date"] = str(value).split(" ")[0]
                        metadata["datetime"] = str(value).replace(":", "-")
                        metadata["year"] = str(value)[:4]
                        metadata["month"] = str(value)[5:7]
                        metadata["day"] = str(value)[8:10]
                        break
                make = exif.get(271)
                model = exif.get(272)
                if make or model:
                    metadata["camera"] = _sanitize_token(f"{make} {model}".strip())
    except Exception:  # noqa: 10 (unknown defaults already set; one corrupt file should not abort the batch)
        pass

    try:
        audio = MutagenFile(file_path, easy=True)
        if audio is not None and getattr(audio, "tags", None):
            tags = audio.tags
            for field in ("title", "artist", "album", "date", "genre"):
                if field in tags:
                    values = tags.get(field)
                    if values:
                        metadata[field] = str(values[0])
            if "tracknumber" in tags and tags["tracknumber"]:
                metadata["track"] = str(tags["tracknumber"][0])
            if "title" in metadata:
                metadata["title"] = _sanitize_token(metadata["title"])
            if "artist" in metadata:
                metadata["artist"] = _sanitize_token(metadata["artist"])
            if "album" in metadata:
                metadata["album"] = _sanitize_token(metadata["album"])
            if "date" in metadata:
                metadata["date"] = str(metadata["date"])[:10]
    except Exception:  # noqa: 10 (unknown defaults already set; one corrupt file should not abort the batch)
        pass

    metadata["camera"] = _sanitize_token(metadata.get("camera", "unknown"))
    metadata["artist"] = _sanitize_token(metadata.get("artist", "unknown"))
    metadata["album"] = _sanitize_token(metadata.get("album", "unknown"))
    return metadata


def render_rename_template(
    file_path: str, template: str, extra_context: dict | None = None
) -> str:
    """Render a filename pattern using metadata tokens such as {date}, {camera}, and {artist}."""
    context = extract_rename_metadata(file_path)
    if extra_context:
        context.update(extra_context)
    rendered = template
    for key, value in list(context.items()):
        rendered = rendered.replace(f"{{{key}}}", _sanitize_token(str(value)))
    rendered = rendered.replace("{ext}", context.get("extension", ""))
    rendered = rendered.replace("{extension}", context.get("extension", ""))
    rendered = rendered.replace(
        "{stem}", context.get("stem", os.path.splitext(os.path.basename(file_path))[0])
    )
    rendered = rendered.replace(
        "{name}", context.get("stem", os.path.splitext(os.path.basename(file_path))[0])
    )
    rendered = rendered.replace("{original}", os.path.basename(file_path))
    return rendered


def _apply_find_replace(
    name: str, ext: str, base_name: str, params: dict
) -> tuple[str, str | None]:
    find_txt = params.get("find", "")
    rep_txt = params.get("replace", "")
    use_regex = params.get("use_regex", False)
    match_ext = params.get("include_extension", False)

    target = base_name if match_ext else name
    new_name = base_name
    error = None
    try:
        if use_regex and find_txt:
            flags = 0 if params.get("case_sensitive", True) else re.IGNORECASE
            res = re.sub(find_txt, rep_txt, target, flags=flags)
        elif find_txt:
            if params.get("case_sensitive", True):
                res = target.replace(find_txt, rep_txt)
            else:
                pattern = re.compile(re.escape(find_txt), re.IGNORECASE)
                res = pattern.sub(rep_txt, target)
        else:
            res = target
        new_name = res if match_ext else f"{res}{ext}"
    except re.error as exc:
        error = f"Regex error: {exc}"
    return new_name, error


def _apply_numbering(
    name: str, ext: str, index: int, params: dict
) -> tuple[str, str | None]:
    prefix = params.get("prefix", "")
    suffix = params.get("suffix", "")
    start = params.get("start", 1)
    step = params.get("step", 1)
    pad = params.get("padding", 3)
    keep_name = params.get("keep_name", False)

    num_str = str(start + index * step).zfill(pad)
    body = f"{name}_{num_str}" if keep_name else f"{prefix}{num_str}{suffix}"
    return f"{body}{ext}", None


def _apply_prefix_suffix(name: str, ext: str, params: dict) -> tuple[str, str | None]:
    prefix = params.get("prefix", "")
    suffix = params.get("suffix", "")
    return f"{prefix}{name}{suffix}{ext}", None


def _apply_change_case(name: str, ext: str, params: dict) -> tuple[str, str | None]:
    case_type = params.get("case_type", "lower")
    affect_ext = params.get("affect_ext", False)
    new_stem = apply_case_transform(name, case_type)
    new_extension = apply_case_transform(ext, case_type) if affect_ext else ext
    return f"{new_stem}{new_extension}", None


def _apply_extension(name: str, params: dict) -> tuple[str, str | None]:
    new_ext = params.get("new_extension", "").strip()
    if new_ext and not new_ext.startswith("."):
        new_ext = f".{new_ext}"
    return f"{name}{new_ext}", None


def _apply_template(old_path: str, ext: str, params: dict) -> tuple[str, str | None]:
    template = params.get("template", "{stem}")
    rendered = render_rename_template(old_path, template)
    if "{ext}" in template or "{extension}" in template:
        new_name = rendered
    else:
        new_name = f"{rendered}{ext}"
    return new_name, None


def preview_renames(
    file_paths: list[str],
    mode: Literal[
        "find_replace",
        "numbering",
        "prefix_suffix",
        "change_case",
        "extension",
        "template",
    ],
    params: dict,
) -> list[RenamePlan]:
    """Generate preview rename plans for a list of file paths without modifying disk."""
    plans: list[RenamePlan] = []
    seen_destinations: set[str] = set()

    for index, old_path in enumerate(file_paths):
        if not os.path.exists(old_path):
            plans.append(
                RenamePlan(
                    old_path,
                    os.path.basename(old_path),
                    os.path.basename(old_path),
                    old_path,
                    error="File not found",
                )
            )
            continue

        dir_name = os.path.dirname(old_path)
        base_name = os.path.basename(old_path)
        name, ext = os.path.splitext(base_name)

        new_name = base_name
        error = None

        if mode == "find_replace":
            new_name, error = _apply_find_replace(name, ext, base_name, params)
        elif mode == "numbering":
            new_name, error = _apply_numbering(name, ext, index, params)
        elif mode == "prefix_suffix":
            new_name, error = _apply_prefix_suffix(name, ext, params)
        elif mode == "change_case":
            new_name, error = _apply_change_case(name, ext, params)
        elif mode == "extension":
            new_name, error = _apply_extension(name, params)
        elif mode == "template":
            new_name, error = _apply_template(old_path, ext, params)

        new_path = os.path.join(dir_name, new_name)
        has_collision = False

        if new_path.lower() in seen_destinations:
            has_collision = True
            error = "Duplicate output filename"
        elif os.path.exists(new_path) and os.path.abspath(new_path) != os.path.abspath(
            old_path
        ):
            has_collision = True
            error = "Destination already exists on disk"

        seen_destinations.add(new_path.lower())
        plans.append(
            RenamePlan(
                old_path=old_path,
                old_name=base_name,
                new_name=new_name,
                new_path=new_path,
                error=error,
                has_collision=has_collision,
            )
        )

    return plans


# ─── Cross-Folder Rename Planning & Timeline Ordering ────────────────────────
def capture_timestamp(file_path: str) -> float:
    """Return the best-known capture time: embedded EXIF/ID3 date, else full-precision mtime."""
    mtime = os.path.getmtime(file_path)
    synthetic = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    metadata = extract_rename_metadata(file_path)
    value = metadata.get("datetime", "")
    if value and value != synthetic:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).timestamp()
            except ValueError:
                continue
    return mtime


def sort_files_by_timeline(file_paths: list[str]) -> list[str]:
    """Sort files from any number of source folders into one chronological timeline."""
    existing = [p for p in file_paths if os.path.exists(p)]
    missing = [p for p in file_paths if p not in existing]
    return sorted(existing, key=capture_timestamp) + missing


def save_cross_folder_plan(
    name: str,
    source_folders: list[str],
    mode: str,
    params: dict,
    target_dir: str | None = None,
    processed_files: list[str] | None = None,
) -> dict:
    """Create a serializable cross-folder rename plan: source folders, rule config, and run history."""
    clean_name = (name or "untitled").strip()
    if not clean_name:
        raise ValueError("Plan name cannot be empty.")
    if not source_folders:
        raise ValueError("A cross-folder plan needs at least one source folder.")
    return {
        "name": clean_name,
        "source_folders": list(source_folders),
        "mode": mode,
        "params": params or {},
        "target_dir": target_dir,
        "processed_files": list(processed_files or []),
    }


def find_new_files_for_plan(
    source_folders: list[str], previously_processed: list[str]
) -> list[str]:
    """Recursively rescan source_folders and return only files not already in previously_processed."""
    processed = set(previously_processed)
    found: list[str] = []
    for folder in source_folders:
        if not os.path.isdir(folder):
            continue
        for root, _, files in os.walk(folder):
            for f in files:
                path = os.path.join(root, f)
                if path not in processed:
                    found.append(path)
    return found


def plan_consolidate_to_folder(
    plans: list[RenamePlan], target_dir: str
) -> list[RenamePlan]:
    """Rewrite a set of rename plans to land in a single destination folder, re-checking collisions."""
    consolidated: list[RenamePlan] = []
    seen_destinations: set[str] = set()

    for plan in plans:
        if plan.error:
            consolidated.append(plan)
            continue

        new_path = os.path.join(target_dir, plan.new_name)
        error = None
        has_collision = False

        if new_path.lower() in seen_destinations:
            has_collision = True
            error = "Duplicate output filename"
        elif os.path.exists(new_path) and os.path.abspath(new_path) != os.path.abspath(
            plan.old_path
        ):
            has_collision = True
            error = "Destination already exists on disk"

        seen_destinations.add(new_path.lower())
        consolidated.append(
            RenamePlan(
                old_path=plan.old_path,
                old_name=plan.old_name,
                new_name=plan.new_name,
                new_path=new_path,
                error=error,
                has_collision=has_collision,
            )
        )

    return consolidated


def execute_renames(plans: list[RenamePlan]) -> list[RenameResult]:
    """Execute rename plans safely on disk with temporary pass for swaps."""
    results: list[RenameResult] = []
    temp_mappings: list[tuple[RenamePlan, str]] = []

    for plan in plans:
        if plan.error or plan.old_path == plan.new_path:
            results.append(
                RenameResult(
                    plan.old_path,
                    plan.new_path,
                    success=(plan.error is None),
                    error=plan.error,
                )
            )
            continue
        temp_path = f"{plan.old_path}.tmp_ren_{os.getpid()}_{id(plan)}"
        try:
            os.rename(plan.old_path, temp_path)
            temp_mappings.append((plan, temp_path))
        except Exception as exc:
            results.append(
                RenameResult(
                    plan.old_path, plan.new_path, success=False, error=str(exc)
                )
            )

    for plan, temp_path in temp_mappings:
        try:
            os.makedirs(os.path.dirname(plan.new_path), exist_ok=True)
            try:
                os.rename(temp_path, plan.new_path)
            except OSError:
                shutil.move(temp_path, plan.new_path)
            results.append(RenameResult(plan.old_path, plan.new_path, success=True))
        except Exception as exc:
            try:
                os.rename(temp_path, plan.old_path)
            except Exception as rollback_exc:
                results.append(
                    RenameResult(
                        plan.old_path,
                        plan.new_path,
                        success=False,
                        error=f"{exc}; rollback also failed, file left at {temp_path}: {rollback_exc}",
                    )
                )
                continue
            results.append(
                RenameResult(
                    plan.old_path, plan.new_path, success=False, error=str(exc)
                )
            )

    return results
