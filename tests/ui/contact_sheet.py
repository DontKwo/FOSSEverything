import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


def build(run_dir_str: str) -> list[str]:
    # Build contact sheet images grouping test screenshots by viewport.
    run_dir = Path(run_dir_str)
    if not run_dir.exists():
        return []

    report_file = run_dir / "report.json"
    error_pngs: set[str] = set()
    if report_file.exists():
        try:
            records = json.loads(report_file.read_text(encoding="utf-8"))
            for rec in records:
                has_err = any(f.get("severity") == "error" for f in rec.get("findings", []))
                if has_err and "png" in rec:
                    error_pngs.add(Path(rec["png"]).resolve().as_posix())
        except Exception:  # noqa: 10
            pass

    png_files = sorted(list(run_dir.rglob("*.png")))
    by_vp: dict[str, list[Path]] = {}
    for p in png_files:
        if p.name.startswith("contact_"):
            continue
        vp_id = p.parent.parent.name if p.parent.parent != run_dir else p.parent.name
        by_vp.setdefault(vp_id, []).append(p)

    output_sheets: list[str] = []
    cols = 4
    thumb_w = 480

    for vp_id, paths in by_vp.items():
        if not paths:
            continue
        num_items = len(paths)
        rows = math.ceil(num_items / cols)
        header_h = 24
        thumb_h = int(thumb_w * 0.6)
        cell_h = thumb_h + header_h + 16
        cell_w = thumb_w + 16
        sheet_w = cols * cell_w
        sheet_h = rows * cell_h

        sheet = Image.new("RGB", (sheet_w, sheet_h), color=(20, 24, 32))
        draw = ImageDraw.Draw(sheet)

        for idx, p in enumerate(paths):
            col = idx % cols
            row = idx // cols
            x = col * cell_w + 8
            y = row * cell_h + 8

            draw.text((x, y), p.stem[:45], fill=(220, 220, 220))

            try:
                img = Image.open(p)
                img.thumbnail((thumb_w, thumb_h), Image.Resampling.BOX)
                sheet.paste(img, (x, y + header_h))

                is_error = p.resolve().as_posix() in error_pngs
                if is_error:
                    draw.rectangle(
                        [x, y + header_h, x + img.width, y + header_h + img.height],
                        outline=(230, 40, 40),
                        width=3,
                    )
            except Exception:  # noqa: 10
                pass

        out_path = run_dir / f"contact_{vp_id}.png"
        sheet.save(str(out_path))
        output_sheets.append(str(out_path.resolve()))

    return output_sheets
