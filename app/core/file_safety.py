"""Safety utilities enforcing non-destructive file operations and collision guards."""
from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path


def compute_path_sha256(file_path: str) -> str:
    # Compute SHA-256 hash of a file for integrity and byte-identity verification.
    hasher = hashlib.sha256()
    with open(file_path, "rb") as stream:
        while chunk := stream.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def generate_safe_output_path(
    source_path: str,
    suffix: str = "_processed",
    target_ext: str | None = None,
    overwrite: bool = False,
) -> str:
    # Generate non-colliding output path ensuring original files remain untouched.
    src = Path(source_path).resolve()
    ext = target_ext if target_ext is not None else src.suffix
    if not ext.startswith(".") and ext:
        ext = f".{ext}"
    parent = src.parent
    base_stem = src.stem

    candidate = parent / f"{base_stem}{suffix}{ext}"
    if overwrite:
        return str(candidate)

    # Avoid colliding with original source file
    if candidate.resolve() == src:
        candidate = parent / f"{base_stem}{suffix}_1{ext}"

    counter = 1
    while candidate.exists():
        candidate = parent / f"{base_stem}{suffix}_{counter}{ext}"
        counter += 1

    return str(candidate)


def check_write_safety(
    destination_path: str,
    source_path: str | None = None,
    overwrite: bool = False,
    required_bytes: int = 0,
) -> None:
    # Ensure write destination does not collide with source and disk has sufficient space.
    dest = Path(destination_path).resolve()

    if source_path:
        src = Path(source_path).resolve()
        if dest == src and not overwrite:
            raise ValueError(f"Unsafe file operation: destination '{dest}' collides with source file.")

    if dest.exists() and not overwrite:
        raise FileExistsError(f"Destination already exists and overwrite is False: '{dest}'")

    parent = dest.parent
    if parent.exists() and required_bytes > 0:
        usage = shutil.disk_usage(parent)
        if usage.free < required_bytes:
            raise OSError(f"Insufficient disk space: {usage.free} bytes available, {required_bytes} bytes required.")
