from typing import Any

from app.features.encoding.ops import (
    base64_decode_text,
    base64_decode_to_file,
    base64_encode_file,
    base64_encode_text,
    binary_decode_to_file,
    binary_encode_file,
    hex_decode_text,
    hex_decode_to_file,
    hex_encode_file,
    hex_encode_text,
    html_decode,
    html_encode,
    html_encode_numeric,
    url_decode,
    url_encode,
)
from app.web.api.result import api_method, fail, ok, require


class EncodingApiMixin:
    @api_method
    def encoding_transform(self, params: dict[str, Any]) -> dict[str, Any]:
        # Transform text using specified encoding method and direction.
        require(params, "text", "method", "direction")
        text = str(params["text"])
        method = str(params["method"]).lower()
        direction = str(params["direction"]).lower()

        if method == "base64":
            res = base64_encode_text(text) if direction == "encode" else base64_decode_text(text)
        elif method == "hex":
            res = hex_encode_text(text) if direction == "encode" else hex_decode_text(text)
        elif method == "url":
            res = url_encode(text) if direction == "encode" else url_decode(text)
        elif method == "html":
            res = html_encode(text) if direction == "encode" else html_decode(text)
        elif method == "html_numeric":
            res = html_encode_numeric(text) if direction == "encode" else html_decode(text)
        else:
            return fail(f"Unsupported encoding method: {method}", code="InvalidMethod")
        return ok(result=res)

    @api_method
    def encoding_base64_encode_text(self, params: dict[str, Any]) -> dict[str, Any]:
        # Encode string to base64 format.
        require(params, "text")
        return ok(result=base64_encode_text(str(params["text"])))

    @api_method
    def encoding_base64_decode_text(self, params: dict[str, Any]) -> dict[str, Any]:
        # Decode base64 string to plain text.
        require(params, "text")
        return ok(result=base64_decode_text(str(params["text"])))

    @api_method
    def encoding_base64_encode_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Encode file contents into base64 text file.
        require(params, "input_path", "output_path")
        base64_encode_file(params["input_path"], params["output_path"])
        return ok(output_path=params["output_path"])

    @api_method
    def encoding_base64_decode_to_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Decode base64 text file into binary output file.
        require(params, "input_path", "output_path")
        base64_decode_to_file(params["input_path"], params["output_path"])
        return ok(output_path=params["output_path"])

    @api_method
    def encoding_hex_encode_text(self, params: dict[str, Any]) -> dict[str, Any]:
        # Encode text to hexadecimal representation.
        require(params, "text")
        spaced = bool(params.get("spaced", False))
        return ok(result=hex_encode_text(str(params["text"]), spaced=spaced))

    @api_method
    def encoding_hex_decode_text(self, params: dict[str, Any]) -> dict[str, Any]:
        # Decode hexadecimal representation to text.
        require(params, "text")
        return ok(result=hex_decode_text(str(params["text"])))

    @api_method
    def encoding_hex_encode_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Encode file contents into hex string file.
        require(params, "input_path", "output_path")
        spaced = bool(params.get("spaced", False))
        hex_encode_file(params["input_path"], params["output_path"], spaced=spaced)
        return ok(output_path=params["output_path"])

    @api_method
    def encoding_hex_decode_to_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Decode hex string file into binary output.
        require(params, "input_path", "output_path")
        hex_decode_to_file(params["input_path"], params["output_path"])
        return ok(output_path=params["output_path"])

    @api_method
    def encoding_binary_encode_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Encode binary file into zero-one string file.
        require(params, "input_path", "output_path")
        binary_encode_file(params["input_path"], params["output_path"])
        return ok(output_path=params["output_path"])

    @api_method
    def encoding_binary_decode_to_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Decode zero-one string file into binary output.
        require(params, "input_path", "output_path")
        binary_decode_to_file(params["input_path"], params["output_path"])
        return ok(output_path=params["output_path"])

    @api_method
    def encoding_url_encode(self, params: dict[str, Any]) -> dict[str, Any]:
        # URL encode input text.
        require(params, "text")
        component = bool(params.get("component", True))
        return ok(result=url_encode(str(params["text"]), component=component))

    @api_method
    def encoding_url_decode(self, params: dict[str, Any]) -> dict[str, Any]:
        # URL decode input text.
        require(params, "text")
        return ok(result=url_decode(str(params["text"])))

    @api_method
    def encoding_html_encode(self, params: dict[str, Any]) -> dict[str, Any]:
        # HTML entity encode input text.
        require(params, "text")
        return ok(result=html_encode(str(params["text"])))

    @api_method
    def encoding_html_encode_numeric(self, params: dict[str, Any]) -> dict[str, Any]:
        # HTML numeric entity encode input text.
        require(params, "text")
        hex_format = bool(params.get("hex_format", False))
        return ok(result=html_encode_numeric(str(params["text"]), hex_format=hex_format))

    @api_method
    def encoding_html_decode(self, params: dict[str, Any]) -> dict[str, Any]:
        # Decode HTML entities into plain text.
        require(params, "text")
        return ok(result=html_decode(str(params["text"])))
