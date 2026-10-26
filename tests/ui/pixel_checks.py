import os
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


def calc_luminance_arr(rgb: np.ndarray) -> np.ndarray:
    # Compute relative luminance matrix for RGB image array.
    r = rgb[:, :, 0].astype(np.float32)
    g = rgb[:, :, 1].astype(np.float32)
    b = rgb[:, :, 2].astype(np.float32)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def analyze(png_path: str, border_rects: list[dict[str, float]] | None = None) -> list[dict[str, Any]]:
    # Perform pixel analysis on screenshot PNG and return finding records.
    findings: list[dict[str, Any]] = []
    p = Path(png_path)
    if not p.exists():
        return [{"id": "P1", "severity": "error", "message": f"Screenshot missing: {png_path}"}]

    img = Image.open(p).convert("RGB")
    arr = np.array(img)
    h, w, _ = arr.shape

    # P1: Check if image is blank
    gray = img.convert("L")
    std = float(np.std(np.array(gray)))
    thumb = img.resize((128, int(128 * h / w)), Image.Resampling.BOX)
    distinct_colors = len(set(np.array(thumb).reshape(-1)))
    if std < 3.0 or distinct_colors < 8:
        findings.append({
            "id": "P1",
            "severity": "error",
            "message": f"Image is blank (std={std:.1f}, distinct_colors={distinct_colors})",
        })

    # P2: Check if content region looks completely empty
    x_start = int(w * 0.20)
    y_start = int(h * 0.08)
    content_area = arr[y_start:, x_start:, :]
    if content_area.size > 0:
        flat = content_area.reshape(-1, 3)
        med_color = np.median(flat, axis=0)
        diff = np.abs(flat.astype(np.float32) - med_color.astype(np.float32))
        non_bg_pixels = np.sum(np.max(diff, axis=1) > 20.0)
        ratio = float(non_bg_pixels) / float(flat.shape[0])
        # Only check P2 on non-empty states (indicated by filename)
        if ("__loaded" in p.name or "__result" in p.name) and ratio < 0.004:
            findings.append({
                "id": "P2",
                "severity": "error",
                "message": f"Content region looks empty ({ratio * 100:.2f}% active pixels)",
            })

    # P3: Content bleeding at right or bottom edge
    lum = calc_luminance_arr(arr)
    bg_lum = float(np.median(lum))
    right_edge_diff = np.abs(lum[:, -1] - bg_lum)
    bottom_edge_diff = np.abs(lum[-1, :] - bg_lum)
    conv_r = np.convolve((right_edge_diff > 40.0).astype(int), np.ones(7, dtype=int), mode="valid")
    consec_right = int(np.max(conv_r)) if conv_r.size > 0 else 0
    conv_b = np.convolve((bottom_edge_diff > 40.0).astype(int), np.ones(7, dtype=int), mode="valid")
    consec_bottom = int(np.max(conv_b)) if conv_b.size > 0 else 0
    if consec_right >= 7 or consec_bottom >= 7:
        findings.append({
            "id": "P3",
            "severity": "warn",
            "message": "Content bleeding at edge (possible clipping)",
        })

    # P5: Perceptual regression check against baseline
    if os.environ.get("FOSS_UI_BASELINE") == "1":
        baseline_path = Path("tests/ui/baselines") / p.name
        if baseline_path.exists():
            base_img = Image.open(baseline_path).convert("RGB")
            if base_img.size == img.size:
                base_arr = np.array(base_img)
                pixel_diff = np.max(np.abs(arr.astype(np.int32) - base_arr.astype(np.int32)), axis=2)
                diff_count = int(np.sum(pixel_diff > 24))
                diff_ratio = float(diff_count) / float(arr.shape[0] * arr.shape[1])
                if diff_ratio > 0.005:
                    findings.append({
                        "id": "P5",
                        "severity": "error",
                        "message": f"Perceptual baseline mismatch ({diff_ratio * 100:.2f}% pixels differ)",
                    })

    return findings
