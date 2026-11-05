import base64
import io
from pathlib import Path
from typing import Any

from PIL import Image

from app.features.data.ops import generate_ics
from app.features.qr.ops import (
    LABEL_SHEET_PRESETS,
    decode_qr_and_barcodes,
    generate_barcode,
    generate_label_sheet,
    generate_qr_code,
    generate_qr_svg,
    generate_qr_with_logo,
    make_asset_tag_payload,
    make_calendar_payload,
    make_email_payload,
    make_geo_payload,
    make_mecard_payload,
    make_phone_payload,
    make_sms_payload,
    make_vcard_payload,
    make_whatsapp_payload,
    make_wifi_payload,
    save_barcode_svg,
    save_qr_code,
    save_qr_svg,
)
from app.web.api.result import api_method, ok, require


def calc_ext_format(path_str: str) -> str:
    # Determine image format identifier from file path extension.
    ext = Path(path_str).suffix.lstrip(".").upper()
    if ext in ("JPG", "JPEG"):
        return "JPEG"
    if ext == "PDF":
        return "PDF"
    if ext == "WEBP":
        return "WEBP"
    return "PNG"


def calc_build_payload(schema: str, params: dict[str, Any]) -> str:
    # Format a standardized QR payload string for a payload schema.
    if schema == "wifi":
        sec = str(params.get("security", params.get("auth_type", "WPA")))
        payload = make_wifi_payload(
            str(params.get("ssid", "")),
            str(params.get("password", "")),
            security=sec,
            hidden=bool(params.get("hidden", False)),
        )
    elif schema == "vcard":
        full_name = str(params.get("name", f"{params.get('first_name', '')} {params.get('last_name', '')}".strip()))
        payload = make_vcard_payload(
            full_name,
            phone=str(params.get("phone", "")),
            email=str(params.get("email", "")),
            org=str(params.get("org", "")),
            title=str(params.get("title", "")),
            url=str(params.get("url", "")),
            note=str(params.get("note", "")),
        )
    elif schema == "mecard":
        payload = make_mecard_payload(
            str(params.get("name", "")),
            phone=str(params.get("phone", "")),
            email=str(params.get("email", "")),
            org=str(params.get("org", "")),
            url=str(params.get("url", "")),
            address=str(params.get("address", "")),
        )
    elif schema == "email":
        payload = make_email_payload(
            str(params.get("email", "")),
            subject=str(params.get("subject", "")),
            body=str(params.get("body", "")),
        )
    elif schema == "sms":
        payload = make_sms_payload(str(params.get("phone", "")), message=str(params.get("message", "")))
    elif schema == "phone":
        payload = make_phone_payload(str(params.get("phone", "")))
    elif schema == "geo":
        payload = make_geo_payload(float(params.get("lat", 0.0)), float(params.get("lon", 0.0)))
    elif schema == "whatsapp":
        payload = make_whatsapp_payload(str(params.get("phone", "")), message=str(params.get("message", "")))
    elif schema == "calendar":
        payload = make_calendar_payload(
            str(params.get("title", "")),
            str(params.get("start_time", "")),
            str(params.get("end_time", "")),
            location=str(params.get("location", "")),
            description=str(params.get("description", "")),
        )
    elif schema == "asset":
        payload = make_asset_tag_payload(
            str(params.get("asset_id", "")),
            location=str(params.get("location", "")),
            owner=str(params.get("owner", "")),
            category=str(params.get("category", "")),
            notes=str(params.get("notes", "")),
        )
    else:
        payload = str(params.get("text", params.get("url", "")))
    return payload


class QrApiMixin:
    @api_method
    def qr_generate(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate a QR bitmap from a payload or schema fields, optionally scaled to size_px and saved.
        if "payload" in params:
            payload = str(params["payload"])
        else:
            require(params, "schema")
            payload = calc_build_payload(str(params["schema"]).lower(), dict(params.get("fields") or {}))
        box_size = int(params.get("box_size", 10))
        border = int(params.get("border", 4))
        fill_color = str(params.get("fill_color", "#000000"))
        back_color = str(params.get("back_color", "#ffffff"))
        err_corr = str(params.get("error_correction", "M"))
        logo_path = params.get("logo_path")

        if logo_path and Path(str(logo_path)).exists():
            img = generate_qr_with_logo(
                payload,
                str(logo_path),
                error_correction=err_corr,
                box_size=box_size,
                border=border,
                fill_color=fill_color,
                back_color=back_color,
            )
        else:
            img = generate_qr_code(
                payload,
                box_size=box_size,
                border=border,
                fill_color=fill_color,
                back_color=back_color,
                error_correction=err_corr,
            )

        size_px = int(params.get("size_px", 0) or 0)
        if size_px > 0:
            img = img.resize((size_px, size_px), Image.NEAREST)

        out_path = params.get("output_path")
        if out_path:
            fmt = calc_ext_format(str(out_path))
            save_qr_code(img, str(out_path), format=fmt)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return ok(
            data_url=f"data:image/png;base64,{data_b64}",
            width=img.width,
            height=img.height,
            output_path=out_path,
            payload=payload,
        )

    @api_method
    def generate_qr(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for QR generation.
        return self.qr_generate(params)

    @api_method
    def qr_generate_svg(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate a vector SVG QR code string and optionally save it to a file.
        if "payload" in params:
            payload = str(params["payload"])
        else:
            require(params, "schema")
            payload = calc_build_payload(str(params["schema"]).lower(), dict(params.get("fields") or {}))
        style = {
            "error_correction": str(params.get("error_correction", "M")),
            "box_size": int(params.get("box_size", 10)),
            "border": int(params.get("border", 4)),
            "fill_color": str(params.get("fill_color", "#000000")),
            "back_color": str(params.get("back_color", "#ffffff")),
        }
        svg_content = generate_qr_svg(payload, **style)
        out_path = params.get("output_path")
        if out_path:
            save_qr_svg(payload, str(out_path), **style)
        return ok(svg=svg_content, output_path=out_path, payload=payload)

    @api_method
    def generate_qr_svg(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for QR SVG generation.
        return self.qr_generate_svg(params)

    @api_method
    def qr_generate_barcode(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate a 1D barcode image (Code128, EAN13, UPC, Code39) and save PNG, JPEG, or SVG output.
        require(params, "payload")
        payload = str(params["payload"])
        bc_type = str(params.get("barcode_type", "code128"))
        include_label = bool(params.get("include_label", True))
        img = generate_barcode(payload, barcode_type=bc_type, include_label=include_label, height=int(params.get("height", 120)))

        out_path = params.get("output_path")
        if out_path:
            if Path(str(out_path)).suffix.lower() == ".svg":
                save_barcode_svg(payload, bc_type, str(out_path), include_label=include_label)
            else:
                save_qr_code(img, str(out_path), format=calc_ext_format(str(out_path)))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return ok(data_url=f"data:image/png;base64,{data_b64}", width=img.width, height=img.height, output_path=out_path)

    @api_method
    def generate_barcode(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for barcode generation.
        return self.qr_generate_barcode(params)

    @api_method
    def qr_decode(self, params: dict[str, Any]) -> dict[str, Any]:
        # Detect and decode QR codes and barcodes from image file.
        require(params, "image_path")
        img_path = str(params["image_path"])
        results = decode_qr_and_barcodes(img_path)
        return ok(results=results, count=len(results), image_path=img_path)

    @api_method
    def qr_decode_data_url(self, params: dict[str, Any]) -> dict[str, Any]:
        # Detect and decode QR codes and barcodes from base64 data URL.
        require(params, "data_url")
        raw_url = str(params["data_url"]).strip()
        if "," in raw_url:
            raw_url = raw_url.split(",", 1)[1]
        img_bytes = base64.b64decode(raw_url)
        img = Image.open(io.BytesIO(img_bytes))
        results = decode_qr_and_barcodes(img)
        return ok(results=results, count=len(results))

    @api_method
    def decode_qr(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for QR and barcode decoding.
        return self.qr_decode(params)

    @api_method
    def qr_build_payload(self, params: dict[str, Any]) -> dict[str, Any]:
        # Format standardized QR payload string for specific schema.
        require(params, "schema")
        schema = str(params["schema"]).lower()
        payload = calc_build_payload(schema, params)
        return ok(payload=payload, schema=schema)

    @api_method
    def qr_label_presets(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return list of printable label sheet presets.
        return ok(presets=list(LABEL_SHEET_PRESETS.keys()))

    @api_method
    def qr_label_sheet(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate printable PDF grid sheet of labels or barcodes.
        require(params, "output_path")
        out_path = str(params["output_path"])
        preset_name = str(params.get("preset", "Avery 5160"))
        matched_preset = None
        preset_clean = preset_name.lower().replace("_", "").replace(" ", "")
        for k in LABEL_SHEET_PRESETS:
            k_clean = k.lower().replace("_", "").replace(" ", "")
            if preset_clean in k_clean or k_clean in preset_clean:
                matched_preset = k
                break
        final_preset = matched_preset or preset_name

        count = int(params.get("count", 30))
        payload = str(params.get("payload", "https://github.com/fosseverything"))
        bc_type = params.get("barcode_type")
        if bc_type:
            img = generate_barcode(payload, barcode_type=str(bc_type))
        else:
            img = generate_qr_code(payload)
        res_p = generate_label_sheet([img] * count, final_preset, out_path)
        presets = list(LABEL_SHEET_PRESETS.keys())
        return ok(output_path=res_p, presets=presets)

    @api_method
    def qr_export_ics(self, params: dict[str, Any]) -> dict[str, Any]:
        # Export calendar event payload as standalone .ics file.
        require(params, "title", "start_time", "output_path")
        title = str(params["title"])
        start = str(params["start_time"])
        out_path = Path(str(params["output_path"])).resolve()
        event = {
            "title": title,
            "start": start,
            "end_time": str(params.get("end_time", "")),
            "location": str(params.get("location", "")),
            "description": str(params.get("description", "")),
        }
        content = generate_ics([event])
        out_path.write_text(content, encoding="utf-8")
        return ok(output_path=str(out_path))
