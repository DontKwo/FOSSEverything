import base64
import io
from pathlib import Path
from typing import Any

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
    save_qr_code,
    save_qr_svg,
)
from app.web.api.result import api_method, ok, require


class QrApiMixin:
    @api_method
    def qr_generate(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate QR code bitmap with custom colors and optional embedded logo.
        require(params, "payload")
        payload = str(params["payload"])
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

        out_path = params.get("output_path")
        if out_path:
            save_qr_code(img, str(out_path))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return ok(data_url=f"data:image/png;base64,{data_b64}", width=img.width, height=img.height, output_path=out_path)

    @api_method
    def generate_qr(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for QR generation.
        return self.qr_generate(params)

    @api_method
    def qr_generate_svg(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate vector SVG string or file for QR code.
        require(params, "payload")
        payload = str(params["payload"])
        svg_content = generate_qr_svg(payload)
        out_path = params.get("output_path")
        if out_path:
            save_qr_svg(payload, str(out_path))
        return ok(svg=svg_content, output_path=out_path)

    @api_method
    def generate_qr_svg(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for QR SVG generation.
        return self.qr_generate_svg(params)

    @api_method
    def qr_generate_barcode(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate 1D barcode image (Code128, EAN13, UPC, Code39).
        require(params, "payload")
        payload = str(params["payload"])
        bc_type = str(params.get("barcode_type", "code128"))
        img = generate_barcode(payload, barcode_type=bc_type)

        out_path = params.get("output_path")
        if out_path:
            img.save(str(out_path))

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
    def decode_qr(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for QR and barcode decoding.
        return self.qr_decode(params)

    @api_method
    def qr_build_payload(self, params: dict[str, Any]) -> dict[str, Any]:
        # Format standardized QR payload string for specific schema.
        require(params, "schema")
        schema = str(params["schema"]).lower()

        if schema == "wifi":
            payload = make_wifi_payload(
                str(params.get("ssid", "")),
                str(params.get("password", "")),
                auth_type=str(params.get("auth_type", "WPA")),
                hidden=bool(params.get("hidden", False)),
            )
        elif schema == "vcard":
            payload = make_vcard_payload(
                first_name=str(params.get("first_name", "")),
                last_name=str(params.get("last_name", "")),
                phone=str(params.get("phone", "")),
                email=str(params.get("email", "")),
                org=str(params.get("org", "")),
                title=str(params.get("title", "")),
                url=str(params.get("url", "")),
            )
        elif schema == "mecard":
            payload = make_mecard_payload(
                str(params.get("name", "")),
                phone=str(params.get("phone", "")),
                email=str(params.get("email", "")),
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
            ics_dummy = generate_ics(str(params.get("title", "")), str(params.get("start_time", "")))
        elif schema == "asset":
            payload = make_asset_tag_payload(
                str(params.get("asset_id", "")),
                name=str(params.get("name", "")),
                model=str(params.get("model", "")),
            )
        else:
            payload = str(params.get("text", ""))

        return ok(payload=payload, schema=schema)

    @api_method
    def qr_label_sheet(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate printable PDF grid sheet of labels or barcodes.
        require(params, "items", "output_path")
        items = list(params["items"])
        out_path = str(params["output_path"])
        preset_name = str(params.get("preset", "Avery 5160"))
        res_p = generate_label_sheet(items, out_path, preset=preset_name)
        presets = list(LABEL_SHEET_PRESETS.keys())
        return ok(output_path=res_p, presets=presets)
