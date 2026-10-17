"""Format naming helpers shared by current and future file tools."""


def normalized_format(format_name: str) -> str:
    """Normalize common aliases to a library-friendly uppercase name."""
    name = format_name.upper().lstrip(".")
    return {"JPG": "JPEG", "TIF": "TIFF", "STP": "STEP", "IGS": "IGES"}.get(name, name)


def extension_for_format(format_name: str) -> str:
    """Return the conventional output extension for a format name."""
    name = normalized_format(format_name)
    return ".jpg" if name == "JPEG" else f".{name.lower()}"


def format_from_path(path: str, default: str = "PNG") -> str:
    """Infer a supported format from an output filename extension."""
    suffix = path.rsplit(".", 1)[-1] if "." in path else default
    return normalized_format(suffix or default)
