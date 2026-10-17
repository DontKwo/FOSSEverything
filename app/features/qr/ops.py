"""Headless QR code generation operations."""
from __future__ import annotations

import io
import urllib.parse
from typing import Any, Literal
from PIL import Image, ImageColor, ImageDraw, ImageFont
import qrcode
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
import cv2
import numpy as np
import pymupdf
import barcode as _barcode_lib
from barcode.writer import ImageWriter

ERROR_CORRECTION_LEVELS = {
    "L": ERROR_CORRECT_L,  # ~7% recovery
    "M": ERROR_CORRECT_M,  # ~15% recovery (default)
    "Q": ERROR_CORRECT_Q,  # ~25% recovery
    "H": ERROR_CORRECT_H,  # ~30% recovery
}


def generate_qr_code(
    payload: str,
    error_correction: str = "M",
    box_size: int = 10,
    border: int = 4,
    fill_color: str | tuple = "black",
    back_color: str | tuple = "white",
) -> Image.Image:
    """Generate a clean QR code Pillow Image from payload text."""
    if not payload:
        payload = " "

    level = ERROR_CORRECTION_LEVELS.get(error_correction.upper(), ERROR_CORRECT_M)
    qr = qrcode.QRCode(
        version=None,
        error_correction=level,
        box_size=max(1, box_size),
        border=max(0, border),
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill_color, back_color=back_color)
    return img.convert("RGBA")


def make_wifi_payload(ssid: str, password: str = "", security: str = "WPA", hidden: bool = False) -> str:
    """Format standard Wi-Fi network configuration QR payload."""
    sec = security.upper()
    if sec not in ("WPA", "WEP", "nopass"):
        sec = "WPA"
    h = "true" if hidden else "false"
    # Escape special characters: '\', ';', ',', ':', '"'
    def esc(text: str) -> str:
        for ch in ("\\", ";", ",", ":", '"'):
            text = text.replace(ch, "\\" + ch)
        return text

    return f"WIFI:T:{sec};S:{esc(ssid)};P:{esc(password)};H:{h};;"


def make_vcard_payload(
    name: str,
    phone: str = "",
    email: str = "",
    org: str = "",
    title: str = "",
    url: str = "",
    note: str = "",
) -> str:
    """Format vCard 3.0 contact payload for address books."""
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"FN:{name}"]
    if org:
        lines.append(f"ORG:{org}")
    if title:
        lines.append(f"TITLE:{title}")
    if phone:
        lines.append(f"TEL;TYPE=CELL:{phone}")
    if email:
        lines.append(f"EMAIL:{email}")
    if url:
        lines.append(f"URL:{url}")
    if note:
        lines.append(f"NOTE:{note}")
    lines.append("END:VCARD")
    return "\n".join(lines)


def make_email_payload(to: str, subject: str = "", body: str = "") -> str:
    """Format mailto URI payload."""
    params = {}
    if subject:
        params["subject"] = subject
    if body:
        params["body"] = body
    query = urllib.parse.urlencode(params)
    return f"mailto:{to}{query}" if query else f"mailto:{to}"


def make_phone_payload(number: str) -> str:
    """Format a tel: URI for a phone number."""
    return f"tel:{number.strip()}" if number.strip() else ""


def make_sms_payload(number: str, message: str = "") -> str:
    """Format an SMS payload that can be parsed by phones and QR readers."""
    number = number.strip()
    if not number:
        return ""
    text = message.strip()
    if text:
        return f"SMSTO:{number}:{text}"
    return f"SMSTO:{number}:"


def make_geo_payload(latitude: float | str, longitude: float | str, altitude: float | str | None = None) -> str:
    """Format a geo: URI pointing to a latitude/longitude coordinate."""
    lat = float(latitude)
    lon = float(longitude)
    if altitude is not None:
        return f"geo:{lat},{lon},{float(altitude)}"
    return f"geo:{lat},{lon}"


def make_calendar_payload(
    summary: str,
    start: str,
    end: str = "",
    location: str = "",
    description: str = "",
    organizer: str = "",
    uid: str = "",
) -> str:
    """Build a vCalendar payload for event invites and meeting QR codes."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "BEGIN:VEVENT",
        f"SUMMARY:{summary}",
        f"DTSTART:{start.replace('-', '').replace(':', '').replace('T', '')}",
    ]
    if end:
        lines.append(f"DTEND:{end.replace('-', '').replace(':', '').replace('T', '')}")
    if location:
        lines.append(f"LOCATION:{location}")
    if description:
        lines.append(f"DESCRIPTION:{description}")
    if organizer:
        lines.append(f"ORGANIZER:{organizer}")
    if uid:
        lines.append(f"UID:{uid}")
    lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\n".join(lines)


def make_mecard_payload(name: str, phone: str = "", email: str = "", org: str = "", url: str = "", address: str = "") -> str:
    """Format a compact MeCard business-card payload for lightweight contact scanning."""
    def esc(text: str) -> str:
        for ch in ("\\", ";", ","):
            text = text.replace(ch, "\\" + ch)
        return text

    parts = [f"N:{esc(name)};"]
    if phone:
        parts.append(f"TEL:{esc(phone)};")
    if email:
        parts.append(f"EMAIL:{esc(email)};")
    if org:
        parts.append(f"ORG:{esc(org)};")
    if address:
        parts.append(f"ADR:{esc(address)};")
    if url:
        parts.append(f"URL:{esc(url)};")
    return "MECARD:" + "".join(parts) + ";"


def make_whatsapp_payload(phone: str, message: str = "") -> str:
    """Format a wa.me deep link that opens a prefilled WhatsApp chat."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not digits:
        return ""
    query = urllib.parse.urlencode({"text": message}) if message else ""
    return f"https://wa.me/{digits}" + (f"?{query}" if query else "")


def make_asset_tag_payload(asset_id: str, location: str = "", owner: str = "", category: str = "", notes: str = "") -> str:
    """Format a structured asset-tracking payload for inventory and equipment tags."""
    fields = [f"ASSET_ID={asset_id.strip()}"]
    if category:
        fields.append(f"CATEGORY={category.strip()}")
    if location:
        fields.append(f"LOCATION={location.strip()}")
    if owner:
        fields.append(f"OWNER={owner.strip()}")
    if notes:
        fields.append(f"NOTES={notes.strip()}")
    return "ASSET:" + ";".join(fields)


def save_qr_code(img: Image.Image, output_path: str, format: str = "PNG") -> str:
    """Save the QR code image to a file path."""
    fmt = format.upper()
    if fmt in ("JPG", "JPEG"):
        rgb = img.convert("RGB")
        rgb.save(output_path, format="JPEG", quality=95)
    elif fmt == "PDF":
        rgb = img.convert("RGB")
        rgb.save(output_path, format="PDF")
    else:
        img.save(output_path, format=fmt)
    return output_path


def generate_qr_with_logo(
    payload: str,
    logo: Image.Image | str,
    logo_scale: float = 0.22,
    error_correction: str = "H",
    box_size: int = 10,
    border: int = 4,
    fill_color: str | tuple = "black",
    back_color: str | tuple = "white",
) -> Image.Image:
    """Generate a high-redundancy QR code with a centered logo image."""
    from PIL import ImageDraw

    # Generate base QR with high error correction (H gives ~30% recovery)
    base_qr = generate_qr_code(
        payload=payload,
        error_correction=error_correction if error_correction in ("Q", "H") else "H",
        box_size=box_size,
        border=border,
        fill_color=fill_color,
        back_color=back_color,
    ).convert("RGBA")

    # Load logo
    if isinstance(logo, str):
        logo_img = Image.open(logo).convert("RGBA")
    else:
        logo_img = logo.convert("RGBA")

    qr_w, qr_h = base_qr.size
    scale = max(0.1, min(0.3, logo_scale))
    target_logo_w = max(16, int(qr_w * scale))
    target_logo_h = max(16, int(qr_h * scale))

    # Resize logo preserving aspect ratio
    logo_img.thumbnail((target_logo_w, target_logo_h), Image.LANCZOS)
    lw, lh = logo_img.size

    # Position in center
    pos_x = (qr_w - lw) // 2
    pos_y = (qr_h - lh) // 2

    # Draw rounded background badge behind logo for high contrast
    pad = 4
    badge_x0 = pos_x - pad
    badge_y0 = pos_y - pad
    badge_x1 = pos_x + lw + pad
    badge_y1 = pos_y + lh + pad

    draw = ImageDraw.Draw(base_qr)
    # Check back_color format
    bg = back_color if isinstance(back_color, (tuple, list)) else (255, 255, 255, 255)
    draw.rounded_rectangle([badge_x0, badge_y0, badge_x1, badge_y1], radius=6, fill=bg)

    base_qr.alpha_composite(logo_img, dest=(pos_x, pos_y))
    return base_qr


def generate_qr_svg(
    payload: str,
    error_correction: str = "M",
    box_size: int = 10,
    border: int = 4,
    fill_color: str = "#000000",  # noqa: 28 (QR pixel color chosen by caller, not app chrome)
    back_color: str = "#ffffff",  # noqa: 28 (QR pixel color chosen by caller, not app chrome)
) -> str:
    """Generate a pure vector SVG XML string for the QR code."""
    if not payload:
        payload = " "

    level = ERROR_CORRECTION_LEVELS.get(error_correction.upper(), ERROR_CORRECT_M)
    qr = qrcode.QRCode(
        version=None,
        error_correction=level,
        box_size=1,
        border=border,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    matrix = qr.get_matrix()
    dim = len(matrix)
    total_size = dim * box_size

    # Build SVG
    svg_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="{total_size}" height="{total_size}" viewBox="0 0 {total_size} {total_size}">',
        f'  <rect width="100%" height="100%" fill="{back_color}"/>',
    ]

    path_data = []
    for r, row in enumerate(matrix):
        for c, cell in enumerate(row):
            if cell:
                x = c * box_size
                y = r * box_size
                path_data.append(f"M{x},{y}h{box_size}v{box_size}h-{box_size}z")

    if path_data:
        svg_parts.append(f'  <path d="{" ".join(path_data)}" fill="{fill_color}"/>')

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)


def save_qr_svg(payload: str, output_path: str, **kwargs: Any) -> str:
    """Save QR code as a vector SVG file."""
    svg_content = generate_qr_svg(payload, **kwargs)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    return output_path


CODE39_PATTERNS = {
    "*": "n n w w n n n n w",
    "0": "n n w n w n n n n",
    "1": "n n n n w n n n w",
    "2": "n n n n n w n n w",
    "3": "n n n n w w n n w",
    "4": "n n n n n n w n w",
    "5": "n n w n n n w n w",
    "6": "n n w n n n n w w",
    "7": "n n n n n w w n w",
    "8": "n n n n w n n w w",
    "9": "n n n n n n n w w",
    "A": "n n w n n w n n w",
    "B": "n n w n n n n w w",
    "C": "n n n w n n n w w",
    "D": "n n n w n n w n w",
    "E": "n n w w n n w n w",
    "F": "n n w w n n n n w",
    "G": "n n n n w n w n w",
    "H": "n n n n w n n w w",
    "I": "n n n w n w n n w",
    "J": "n n n w n n w w w",
    "K": "n n w n n w n w n",
    "L": "n n w n n n n n w",
    "M": "n n n w n n n w w",
    "N": "n n n w n n w w n",
    "O": "n n w w n n w w n",
    "P": "n n w w n n n n n",
    "Q": "n n n n w n w w n",
    "R": "n n n n w n n w n",
    "S": "n n n w n w n w n",
    "T": "n n n w n n n w n",
    "U": "n n w n w n n n w",
    "V": "n n w n w n n w n",
    "W": "n n n w w n n w n",
    "X": "n n w n n w n w n",
    "Y": "n n w n n n w n w",
    "Z": "n n n w n n w n w",
    "-": "n n w n w n w n n",
    ".": "n n w n w n n w n",
    " ": "n n w n w n w n w",
    "$": "n n w n n w n w n",
    "/": "n n n w n n n w n",
    "+": "n n n w n w n n n",
    "%": "n n n n w n w n n",
}


LIBRARY_BARCODE_TYPES = {"code128", "ean13", "ean8", "upca", "itf"}


def _normalize_color(color: str | tuple[int, int, int]) -> tuple[int, int, int]:
    if isinstance(color, str):
        return ImageColor.getrgb(color)
    return tuple(color)


def _generate_library_barcode(
    value: str,
    barcode_type: str,
    *,
    include_label: bool = False,
    foreground: tuple[int, int, int] | str = "black",
    background: tuple[int, int, int] | str = "white",
) -> Image.Image:
    text = (value or "").strip()
    if not text:
        raise ValueError("Barcode value cannot be empty.")
    fg = _normalize_color(foreground)
    bg = _normalize_color(background)

    barcode_class = _barcode_lib.get_barcode_class(barcode_type)
    instance = barcode_class(text, writer=ImageWriter())
    options = {
        "write_text": include_label,
        "foreground": f"#{fg[0]:02x}{fg[1]:02x}{fg[2]:02x}",
        "background": f"#{bg[0]:02x}{bg[1]:02x}{bg[2]:02x}",
        "quiet_zone": 2.0,
    }
    img = instance.render(options)
    return img.convert("RGBA")


def generate_barcode(
    value: str,
    barcode_type: str = "code39",
    *,
    width: int = 2,
    height: int = 120,
    include_label: bool = False,
    foreground: tuple[int, int, int] | str = "black",
    background: tuple[int, int, int] | str = "white",
) -> Image.Image:
    """Generate a local barcode image (Code 39, Code 128, EAN-13/8, UPC-A, or ITF)."""
    barcode_type = (barcode_type or "code39").lower()
    if barcode_type in LIBRARY_BARCODE_TYPES:
        return _generate_library_barcode(
            value, barcode_type, include_label=include_label, foreground=foreground, background=background
        )
    if barcode_type != "code39":
        raise ValueError(f"Unsupported barcode type: {barcode_type}")
    text = (value or "").strip()
    if not text:
        raise ValueError("Barcode value cannot be empty.")

    fg = _normalize_color(foreground)
    bg = _normalize_color(background)

    code = "*" + text.upper() + "*"
    valid = set(CODE39_PATTERNS)
    if any(ch not in valid for ch in code):
        raise ValueError(f"Unsupported character in Code 39 barcode: {''.join(sorted(set(code) - valid))}")

    cell_width = max(1, int(width))
    segments = []
    for ch in code:
        pattern = CODE39_PATTERNS[ch].split()
        segments.extend(pattern)
        segments.append("n")

    total_pixels = sum((1 if token == "n" else 2) for token in segments) * cell_width
    image = Image.new("RGBA", (total_pixels + 2, max(20, int(height))), bg + (255,))
    draw = ImageDraw.Draw(image)

    current_x = 0
    for idx, token in enumerate(segments):
        segment_width = (1 if token == "n" else 2) * cell_width
        if idx % 2 == 0:
            draw.rectangle((current_x, 0, current_x + segment_width - 1, image.height - 1), fill=fg + (255,))
        current_x += segment_width

    if include_label:
        font = ImageFont.load_default()
        label_y = max(0, height - 16)
        draw.text((6, label_y), value.upper(), font=font, fill=fg + (255,))
    return image


# ─── Decoding & Parsing ──────────────────────────────────────────────────────
def parse_qr_payload(payload: str) -> dict:
    """Parse standard payload prefixes (URL, Wi-Fi, vCard, Email, SMS, Phone)."""
    text = payload.strip()
    if not text:
        return {"type": "empty", "title": "Empty", "data": {}}

    # Wi-Fi: WIFI:T:WPA;S:Network;P:Pass;H:false;;
    if text.startswith("WIFI:"):
        data = {}
        body = text[5:].rstrip(";")
        tokens = body.split(";")
        for tok in tokens:
            if ":" in tok:
                k, v = tok.split(":", 1)
                if k == "T":
                    data["security"] = v
                elif k == "S":
                    data["ssid"] = v
                elif k == "P":
                    data["password"] = v
                elif k == "H":
                    data["hidden"] = v.lower() == "true"
        return {
            "type": "wifi",
            "title": f"Wi-Fi Network: {data.get('ssid', 'Unknown')}",
            "data": data,
            "raw": text,
        }

    # URL
    if text.startswith(("http://", "https://", "ftp://", "www.")):
        url = text if not text.startswith("www.") else f"https://{text}"
        return {"type": "url", "title": "Website URL", "url": url, "raw": text}

    # Email
    if text.startswith("mailto:"):
        return {"type": "email", "title": "Email Link", "email": text[7:], "raw": text}

    # Phone / SMS
    if text.startswith("tel:"):
        return {"type": "phone", "title": "Phone Number", "phone": text[4:], "raw": text}
    if text.startswith("SMSTO:"):
        body = text[6:]
        if ":" in body:
            number, message = body.split(":", 1)
            return {"type": "sms", "title": "SMS Message", "number": number, "message": message, "raw": text}
        return {"type": "sms", "title": "SMS Message", "number": body, "message": "", "raw": text}

    # Geo coordinates
    if text.startswith("geo:"):
        coords = text[4:]
        try:
            parts = coords.split(",")
            lat = float(parts[0]) if len(parts) > 0 else None
            lon = float(parts[1]) if len(parts) > 1 else None
            return {"type": "geo", "title": "Location", "latitude": lat, "longitude": lon, "raw": text}
        except ValueError:  # noqa: 10 (unparsable geo payload falls through to plain-text classification)
            pass

    # vCard / calendar
    if text.startswith("BEGIN:VCARD"):
        return {"type": "vcard", "title": "Contact Card (vCard)", "raw": text}
    if text.startswith("BEGIN:VCALENDAR"):
        return {"type": "calendar", "title": "Calendar Event", "raw": text}

    return {"type": "text", "title": "Plain Text", "raw": text}


# ─── Print-Ready Label Sheets ────────────────────────────────────────────────
# Dimensions in PDF points (72pt = 1 inch), matching published Avery template specs.
LABEL_SHEET_PRESETS: dict[str, dict[str, float | int]] = {
    "Avery 5160 (30-up Address, 1\" x 2.625\")": {
        "page_w": 612, "page_h": 792,
        "label_w": 189, "label_h": 72,
        "columns": 3, "rows": 10,
        "top_margin": 36, "left_margin": 13.5,
        "h_gutter": 9, "v_gutter": 0,
    },
    "Avery 5163 (10-up Shipping, 2\" x 4\")": {
        "page_w": 612, "page_h": 792,
        "label_w": 288, "label_h": 144,
        "columns": 2, "rows": 5,
        "top_margin": 36, "left_margin": 13.5,
        "h_gutter": 9, "v_gutter": 0,
    },
    "2x2 in Square Labels (Generic)": {
        "page_w": 612, "page_h": 792,
        "label_w": 144, "label_h": 144,
        "columns": 3, "rows": 5,
        "top_margin": 18, "left_margin": 18,
        "h_gutter": 9, "v_gutter": 9,
    },
    "1x1 in Square Labels (Generic)": {
        "page_w": 612, "page_h": 792,
        "label_w": 72, "label_h": 72,
        "columns": 6, "rows": 8,
        "top_margin": 36, "left_margin": 36,
        "h_gutter": 9, "v_gutter": 9,
    },
}


def _label_cell_rects(preset: dict[str, float | int]) -> list["pymupdf.Rect"]:
    rects: list[pymupdf.Rect] = []
    label_w, label_h = preset["label_w"], preset["label_h"]
    h_pitch = label_w + preset["h_gutter"]
    v_pitch = label_h + preset["v_gutter"]
    for row in range(int(preset["rows"])):
        for col in range(int(preset["columns"])):
            x0 = preset["left_margin"] + col * h_pitch
            y0 = preset["top_margin"] + row * v_pitch
            rects.append(pymupdf.Rect(x0, y0, x0 + label_w, y0 + label_h))
    return rects


def generate_label_sheet(
    codes: list[Image.Image],
    preset_name: str,
    output_path: str,
    labels_text: list[str] | None = None,
) -> str:
    """Tile QR/barcode images onto print-ready label sheet page(s) at exact physical size."""
    if not codes:
        raise ValueError("At least one code image is required.")
    preset = LABEL_SHEET_PRESETS.get(preset_name)
    if preset is None:
        raise ValueError(f"Unknown label sheet preset: {preset_name}")

    cell_rects = _label_cell_rects(preset)
    cells_per_page = len(cell_rects)

    if len(codes) < cells_per_page:
        pages_of_codes = [[codes[i % len(codes)] for i in range(cells_per_page)]]
        pages_of_labels = [[(labels_text[i % len(labels_text)] if labels_text else None) for i in range(cells_per_page)]]
    else:
        pages_of_codes = [codes[i:i + cells_per_page] for i in range(0, len(codes), cells_per_page)]
        if labels_text:
            pages_of_labels = [labels_text[i:i + cells_per_page] for i in range(0, len(labels_text), cells_per_page)]
        else:
            pages_of_labels = [[None] * len(chunk) for chunk in pages_of_codes]

    doc = pymupdf.open()
    for page_codes, page_labels in zip(pages_of_codes, pages_of_labels):
        page = doc.new_page(width=preset["page_w"], height=preset["page_h"])
        for rect, code_img, label in zip(cell_rects, page_codes, page_labels):
            buffer = io.BytesIO()
            code_img.convert("RGB").save(buffer, format="PNG")
            caption_h = 10 if label else 0
            image_rect = pymupdf.Rect(rect.x0, rect.y0, rect.x1, rect.y1 - caption_h)
            page.insert_image(image_rect, stream=buffer.getvalue())
            if label:
                page.insert_text(
                    (rect.x0 + 2, rect.y1 - 2),
                    label,
                    fontsize=7,
                    fontname="helv",
                )
    doc.save(output_path)
    doc.close()
    return output_path


def decode_qr_and_barcodes(source: str | Image.Image | object) -> list[dict]:
    """Decode all QR codes and barcodes found in an image, document, or OpenCV frame."""
    if isinstance(source, str):
        if source.lower().endswith(".pdf"):
            doc = pymupdf.open(source)
            results = []
            for pno in range(len(doc)):
                page = doc[pno]
                pix = page.get_pixmap(dpi=150)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                res = decode_qr_and_barcodes(img)
                for r in res:
                    r["page"] = pno + 1
                results.extend(res)
            return results
        else:
            pil_img = Image.open(source)
    elif isinstance(source, Image.Image):
        pil_img = source
    elif type(source).__module__ == "numpy":
        arr = np.asarray(source)
        if arr.ndim == 2:
            pil_img = Image.fromarray(arr, mode="L")
        elif arr.shape[2] == 4:
            pil_img = Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGRA2RGBA))
        else:
            pil_img = Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))
    else:
        raise ValueError(f"Unsupported source type: {type(source)}")

    # Convert to RGB numpy array
    rgb_arr = np.array(pil_img.convert("RGB"))
    gray_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2GRAY)

    results = []
    seen_payloads = set()

    # 1. OpenCV QR Code Detector (Multi & Single)
    qr_detector = cv2.QRCodeDetector()

    # Try multi on RGB and Grayscale
    for arr in (gray_arr, rgb_arr):
        try:
            ok, decoded_info, points, _ = qr_detector.detectAndDecodeMulti(arr)
            if ok and decoded_info:
                for idx, text in enumerate(decoded_info):
                    text = text.strip()
                    if text and text not in seen_payloads:
                        seen_payloads.add(text)
                        pts = points[idx].tolist() if points is not None and len(points) > idx else []
                        results.append({
                            "type": "QR Code",
                            "payload": text,
                            "parsed": parse_qr_payload(text),
                            "points": pts,
                        })
        except Exception:
            continue

    # Single fallback if multi missed
    if not results:
        for arr in (gray_arr, rgb_arr):
            try:
                val, pts, _ = qr_detector.detectAndDecode(arr)
                val = val.strip()
                if val and val not in seen_payloads:
                    seen_payloads.add(val)
                    results.append({
                        "type": "QR Code",
                        "payload": val,
                        "parsed": parse_qr_payload(val),
                        "points": pts.tolist() if pts is not None else [],
                    })
            except Exception:
                continue

    # 2. OpenCV Barcode Detector
    try:
        if hasattr(cv2, "barcode") and hasattr(cv2.barcode, "BarcodeDetector"):
            barcode_detector = cv2.barcode.BarcodeDetector()
            ok, decoded_info, decoded_type, points = barcode_detector.detectAndDecode(gray_arr)
            if ok and decoded_info:
                for idx, text in enumerate(decoded_info):
                    text = text.strip()
                    if text and text not in seen_payloads:
                        seen_payloads.add(text)
                        b_type = decoded_type[idx] if decoded_type is not None and len(decoded_type) > idx else "Barcode"
                        results.append({
                            "type": f"Barcode ({b_type})",
                            "payload": text,
                            "parsed": parse_qr_payload(text),
                            "points": points[idx].tolist() if points is not None and len(points) > idx else [],
                        })
    except Exception:  # noqa: 10 (final fallback stage; no more detectors to try)
        pass

    return results


