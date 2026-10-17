"""Headless data formatting, minification, syntax validation, and conversion."""
from __future__ import annotations

import csv
import difflib
import html
import io
import json
import os
import random
import re
import string
import uuid
import xml.dom.minidom
import xml.etree.ElementTree as ET
import configparser
from datetime import datetime, timedelta, timezone
from typing import Any

import tomllib
import yaml
import language_tool_python
import sqlparse
import jsbeautifier
import cssbeautifier

DATA_FORMATS = ["JSON", "YAML", "CSV", "TOML", "INI"]
DATA_EXTENSIONS = {
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".csv": "CSV",
    ".toml": "TOML",
    ".ini": "INI",
}


def data_format_for_path(path: str) -> str | None:
    """Return the normalized data format for a file path if supported."""
    ext = os.path.splitext(path)[1].lower()
    return DATA_EXTENSIONS.get(ext)


def _toml_dumps(data: Any) -> str:
    """Serialize a simple dict/list structure to TOML without extra dependencies."""
    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"[{key}]")
                for sub_key, sub_value in value.items():
                    lines.append(f"{sub_key} = {_toml_scalar(sub_value)}")
                lines.append("")
            else:
                lines.append(f"{key} = {_toml_scalar(value)}")
        return "\n".join(lines).rstrip() + "\n"
    if isinstance(data, list):
        return "\n".join(f"items = {_toml_scalar(data)}")
    return _toml_scalar(data)


def _toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return '""'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_scalar(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{json.dumps(k)}: {_toml_scalar(v)}" for k, v in value.items()) + "}"
    return json.dumps(str(value), ensure_ascii=False)


def _ini_to_dict(text: str) -> dict[str, dict[str, str]]:
    parser = configparser.ConfigParser()
    parser.read_string(text)
    return {section: dict(parser[section]) for section in parser.sections()}


def load_data(path: str) -> Any:
    """Load structured data from a JSON, YAML, CSV, TOML, or INI file path."""
    fmt = data_format_for_path(path)
    if fmt is None:
        raise ValueError(f"Unsupported data file extension for {path}")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if fmt == "JSON":
        return json.loads(content)
    elif fmt == "YAML":
        if yaml is None:
            raise RuntimeError("PyYAML is not installed.")
        return yaml.safe_load(content)
    elif fmt == "CSV":
        reader = csv.DictReader(io.StringIO(content))
        return list(reader)
    elif fmt == "TOML":
        return tomllib.loads(content)
    elif fmt == "INI":
        return _ini_to_dict(content)
    return content


def save_data(data: Any, output_path: str, format_name: str) -> str:
    """Save structured data to a destination path in JSON, YAML, CSV, TOML, or INI format."""
    fmt = format_name.upper()
    if fmt == "JSON":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    elif fmt == "YAML":
        if yaml is None:
            raise RuntimeError("PyYAML is not installed.")
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False, indent=2, allow_unicode=True)
    elif fmt == "CSV":
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list) or not data or not all(isinstance(row, dict) for row in data):
            raise ValueError("CSV conversion requires a list of flat dictionaries.")
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            headers = list(data[0].keys())
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
    elif fmt == "TOML":
        if not isinstance(data, dict):
            raise ValueError("TOML export requires a dictionary payload.")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(_toml_dumps(data))
    elif fmt == "INI":
        if not isinstance(data, dict):
            raise ValueError("INI export requires a dictionary payload.")
        parser = configparser.ConfigParser()
        for section, values in data.items():
            if isinstance(values, dict):
                parser[section] = {str(k): str(v) for k, v in values.items()}
            else:
                if "settings" not in parser:
                    parser["settings"] = {}
                parser["settings"][str(section)] = str(values)
        with open(output_path, "w", encoding="utf-8") as f:
            parser.write(f)
    else:
        raise ValueError(f"Unsupported target format: {format_name}")
    return output_path


def format_json(text: str, indent: int = 2) -> str:
    """Format and pretty-print JSON string."""
    parsed = json.loads(text)
    return json.dumps(parsed, indent=indent, ensure_ascii=False)


def minify_json(text: str) -> str:
    """Minify JSON by removing unnecessary whitespace."""
    parsed = json.loads(text)
    return json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)


def format_yaml(text: str, indent: int = 2) -> str:
    """Format and validate YAML document."""
    if yaml is None:
        raise RuntimeError("PyYAML is not installed.")
    parsed = yaml.safe_load(text)
    return yaml.dump(parsed, sort_keys=False, indent=indent, allow_unicode=True)


def format_xml(text: str, indent: int = 2) -> str:
    """Format and pretty-print XML string."""
    dom = xml.dom.minidom.parseString(text)
    return dom.toprettyxml(indent=" " * indent)


def minify_xml(text: str) -> str:
    """Minify XML string."""
    root = ET.fromstring(text)
    return ET.tostring(root, encoding="unicode", method="xml").strip()


def format_sql(text: str) -> str:
    """Format and pretty-print SQL with reindented, uppercase-keyword output."""
    return sqlparse.format(text, reindent=True, keyword_case="upper")  # noqa: 16 (sqlparse.format is a library call, not str.format)


def minify_sql(text: str) -> str:
    """Minify SQL by stripping comments and collapsing whitespace."""
    stripped = sqlparse.format(text, strip_comments=True, reindent=False)  # noqa: 16 (sqlparse.format is a library call, not str.format)
    return re.sub(r"\s+", " ", stripped).strip()


def format_javascript(text: str) -> str:
    """Format and pretty-print JavaScript using jsbeautifier."""
    return jsbeautifier.beautify(text)


_JS_STRING_OR_COMMENT_RE = re.compile(
    r"(/\*.*?\*/|//[^\n]*|'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`)",
    re.DOTALL,
)


def _strip_js_comment_token(match: re.Match) -> str:
    token = match.group(0)
    return "" if token.startswith("/*") or token.startswith("//") else token


def minify_javascript(text: str) -> str:
    """Conservative heuristic JS minifier: strips // and /* */ comments outside string/template
    literals and collapses whitespace. This is not a full parser (e.g. it does not disambiguate
    regex literals from division), so it is meant for quick cleanup rather than production output."""
    stripped = _JS_STRING_OR_COMMENT_RE.sub(_strip_js_comment_token, text)
    return re.sub(r"\s+", " ", stripped).strip()


def format_css(text: str) -> str:
    """Format and pretty-print CSS using cssbeautifier."""
    return cssbeautifier.beautify(text)


_CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def minify_css(text: str) -> str:
    """Conservative heuristic CSS minifier: strips /* */ comments and collapses whitespace/
    separators. This is not a full parser, so unusual constructs may not compress optimally."""
    stripped = _CSS_COMMENT_RE.sub("", text)
    stripped = re.sub(r"\s+", " ", stripped)
    stripped = re.sub(r"\s*([{}:;,])\s*", r"\1", stripped)
    stripped = re.sub(r";}", "}", stripped)
    return stripped.strip()


def validate_syntax(text: str, format_type: str) -> tuple[bool, str, int | None]:
    """Validate data syntax. Returns (is_valid, message, line_number)."""
    fmt = format_type.lower()
    if not text.strip():
        return True, "Empty content", None

    if fmt == "json":
        try:
            json.loads(text)
            return True, "Valid JSON", None
        except json.JSONDecodeError as exc:
            return False, f"JSON Error: {exc.msg}", exc.lineno

    elif fmt == "yaml":
        if yaml is None:
            return True, "YAML validator not installed", None
        try:
            yaml.safe_load(text)
            return True, "Valid YAML", None
        except yaml.YAMLError as exc:
            line = None
            if hasattr(exc, "problem_mark") and exc.problem_mark:
                line = exc.problem_mark.line + 1
            return False, f"YAML Error: {exc}", line

    elif fmt == "xml":
        try:
            ET.fromstring(text)
            return True, "Valid XML", None
        except ET.ParseError as exc:
            line, _ = exc.position
            return False, f"XML Error: {exc}", line

    elif fmt == "csv":
        try:
            reader = csv.reader(io.StringIO(text))
            list(reader)
            return True, "Valid CSV", None
        except Exception as exc:
            return False, f"CSV Error: {exc}", None
    elif fmt == "toml":
        try:
            tomllib.loads(text)
            return True, "Valid TOML", None
        except Exception as exc:
            return False, f"TOML Error: {exc}", None
    elif fmt == "ini":
        try:
            parser = configparser.ConfigParser()
            parser.read_string(text)
            return True, "Valid INI", None
        except Exception as exc:
            return False, f"INI Error: {exc}", None
    elif fmt == "sql":
        parsed = sqlparse.parse(text)
        if not parsed or not any(str(stmt).strip() for stmt in parsed):
            return False, "SQL Error: no statements parsed", None
        return True, "Valid SQL (heuristic)", None

    return True, "Valid", None


def convert_data_format(text: str, from_format: str, to_format: str) -> str:
    """Convert structured text among JSON, YAML, CSV, TOML, and INI."""
    from_fmt = from_format.lower()
    to_fmt = to_format.lower()

    if from_fmt == to_fmt:
        return text

    if from_fmt == "json":
        data = json.loads(text)
    elif from_fmt == "yaml":
        if yaml is None:
            raise RuntimeError("PyYAML not installed.")
        data = yaml.safe_load(text)
    elif from_fmt == "csv":
        reader = csv.DictReader(io.StringIO(text))
        data = list(reader)
    elif from_fmt == "toml":
        data = tomllib.loads(text)
    elif from_fmt == "ini":
        parser = configparser.ConfigParser()
        parser.read_string(text)
        data = {section: dict(parser[section]) for section in parser.sections()}
    else:
        raise ValueError(f"Unsupported source format: {from_format}")

    if to_fmt == "json":
        return json.dumps(data, indent=2, ensure_ascii=False)
    elif to_fmt == "yaml":
        if yaml is None:
            raise RuntimeError("PyYAML not installed.")
        return yaml.dump(data, sort_keys=False, indent=2, allow_unicode=True)
    elif to_fmt == "csv":
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list) or not data or not all(isinstance(row, dict) for row in data):
            raise ValueError("CSV conversion requires a list of flat dictionaries.")
        output = io.StringIO()
        headers = list(data[0].keys())
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
    elif to_fmt == "toml":
        if not isinstance(data, dict):
            raise ValueError("TOML conversion requires dictionary data.")
        return _toml_dumps(data)
    elif to_fmt == "ini":
        if not isinstance(data, dict):
            raise ValueError("INI conversion requires dictionary data.")
        parser = configparser.ConfigParser()
        for section, values in data.items():
            if isinstance(values, dict):
                parser[section] = {str(k): str(v) for k, v in values.items()}
            else:
                if "settings" not in parser:
                    parser["settings"] = {}
                parser["settings"][str(section)] = str(values)
        output = io.StringIO()
        parser.write(output)
        return output.getvalue()
    else:
        raise ValueError(f"Unsupported target format: {to_format}")


def convert_units(value: float, from_unit: str, to_unit: str, category: str | None = None) -> float:
    """Convert between supported unit values for a category or by auto-detecting the pair.

    Supported categories: length, weight, temperature, time, area, volume, speed,
    pressure, angle, and data.
    """
    category_map = {
        "length": {"mm": 1.0, "cm": 10.0, "m": 1000.0, "km": 1000000.0, "in": 25.4, "ft": 304.8, "yd": 914.4, "mi": 1609344.0},
        "temperature": {"c": 1.0, "f": 1.0, "k": 1.0},
        "weight": {"mg": 1.0, "g": 1000.0, "kg": 1000000.0, "oz": 28349.523125, "lb": 453592.37, "st": 6350293.18},
        "time": {"ms": 1.0, "s": 1000.0, "min": 60000.0, "h": 3600000.0, "day": 86400000.0},
        "area": {"mm2": 1.0, "cm2": 100.0, "m2": 1000000.0, "km2": 1000000000000.0, "in2": 645.16, "ft2": 92903.04, "yd2": 836127.36, "ac": 4046856422.4, "ha": 10000000000.0},
        "volume": {"ml": 1.0, "l": 1000.0, "m3": 1000000.0, "us_fl_oz": 29.5735295625, "cup": 236.5882365, "pt": 473.176473, "qt": 946.352946, "gal": 3785.411784},
        "speed": {"mps": 1.0, "kmh": 0.2777777777777778, "mph": 0.44704, "knot": 0.5144444444444445},
        "pressure": {"pa": 1.0, "kpa": 1000.0, "mpa": 1000000.0, "bar": 100000.0, "psi": 6894.757293168361},
        "angle": {"rad": 1.0, "deg": 0.017453292519943295, "grad": 0.015707963267948967, "turn": 6.283185307179586},
        "data": {"b": 1.0, "kb": 1000.0, "mb": 1000000.0, "gb": 1000000000.0, "tb": 1000000000000.0, "kib": 1024.0, "mib": 1048576.0, "gib": 1073741824.0},
    }

    def normalize_unit(unit: str) -> str:
        cleaned = unit.strip().lower().replace(" ", "_")
        aliases = {
            "m": "m", "meter": "m", "metre": "m",
            "km": "km", "kilometer": "km", "kilometre": "km",
            "cm": "cm", "centimeter": "cm", "centimetre": "cm",
            "mm": "mm", "millimeter": "mm", "millimetre": "mm",
            "in": "in", "inch": "in", "inches": "in",
            "ft": "ft", "foot": "ft", "feet": "ft",
            "yd": "yd", "yard": "yd", "yards": "yd",
            "mi": "mi", "mile": "mi", "miles": "mi",
            "g": "g", "gram": "g", "grams": "g",
            "kg": "kg", "kilogram": "kg", "kilograms": "kg",
            "mg": "mg", "milligram": "mg",
            "oz": "oz", "ounce": "oz", "ounces": "oz",
            "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
            "st": "st", "stone": "st",
            "s": "s", "second": "s", "seconds": "s",
            "ms": "ms", "millisecond": "ms", "milliseconds": "ms",
            "min": "min", "minute": "min", "minutes": "min",
            "h": "h", "hr": "h", "hour": "h", "hours": "h",
            "day": "day", "days": "day",
            "c": "c", "celsius": "c",
            "f": "f", "fahrenheit": "f",
            "k": "k", "kelvin": "k",
            "deg": "deg", "degree": "deg", "degrees": "deg",
            "rad": "rad", "radian": "rad", "radians": "rad",
            "turn": "turn", "revolution": "turn", "revolutions": "turn",
            "grad": "grad", "gon": "grad",
            "pa": "pa", "pascal": "pa",
            "kpa": "kpa", "kilopascal": "kpa",
            "mpa": "mpa", "megapascal": "mpa",
            "bar": "bar",
            "psi": "psi",
            "mps": "mps", "m/s": "mps",
            "kmh": "kmh", "km/h": "kmh",
            "mph": "mph", "mi/h": "mph",
            "knot": "knot", "knots": "knot",
            "b": "b", "bit": "b", "bits": "b",
            "kb": "kb", "kib": "kib", "mb": "mb", "mib": "mib", "gb": "gb", "gib": "gib", "tb": "tb",
            "l": "l", "liter": "l", "litre": "l",
            "ml": "ml", "milliliter": "ml", "millilitre": "ml",
            "m3": "m3", "m^3": "m3", "cubic_meter": "m3",
            "us_fl_oz": "us_fl_oz", "floz": "us_fl_oz",
            "cup": "cup",
            "pt": "pt", "pint": "pt",
            "qt": "qt", "quart": "qt",
            "gal": "gal", "gallon": "gal",
        }
        return aliases.get(cleaned, cleaned)

    if category is None:
        source = normalize_unit(from_unit)
        target = normalize_unit(to_unit)
        detected = None
        for key, units in category_map.items():
            if source in units and target in units:
                detected = key
                break
        if detected is None:
            raise ValueError(f"Unsupported unit conversion: {from_unit} -> {to_unit}")
        category = detected

    key = category.lower().replace(" ", "_")
    if key not in category_map:
        raise ValueError(f"Unsupported unit category: {category}")

    source = normalize_unit(from_unit)
    target = normalize_unit(to_unit)
    if source == target:
        return float(value)

    if key == "temperature":
        if source == "c" and target == "f":
            return (value * 9.0 / 5.0) + 32.0
        if source == "f" and target == "c":
            return (value - 32.0) * 5.0 / 9.0
        if source == "c" and target == "k":
            return value + 273.15
        if source == "k" and target == "c":
            return value - 273.15
        if source == "f" and target == "k":
            return ((value - 32.0) * 5.0 / 9.0) + 273.15
        if source == "k" and target == "f":
            return ((value - 273.15) * 9.0 / 5.0) + 32.0
        raise ValueError(f"Unsupported temperature conversion: {from_unit} -> {to_unit}")

    units = category_map[key]
    if source not in units or target not in units:
        raise ValueError(f"Unsupported unit conversion for {category}: {from_unit} -> {to_unit}")

    base_value = value * units[source]
    return base_value / units[target]


def generate_random_value(kind: str = "string", length: int = 12, *, count: int = 1, min_value: int = 0, max_value: int = 100,
                          include_uppercase: bool = True, include_lowercase: bool = True, include_digits: bool = True,
                          include_symbols: bool = False, custom_alphabet: str | None = None) -> str | int | list[str | int]:
    """Generate random values for strings, numbers, passwords, names, and UUIDs."""
    kind = kind.lower()
    if kind in {"password", "token", "string"}:
        alphabet_chars = []
        if include_lowercase:
            alphabet_chars.append(string.ascii_lowercase)
        if include_uppercase:
            alphabet_chars.append(string.ascii_uppercase)
        if include_digits:
            alphabet_chars.append(string.digits)
        if include_symbols:
            alphabet_chars.append(string.punctuation)
        alphabet = custom_alphabet or "".join(alphabet_chars)
        if not alphabet:
            raise ValueError("At least one character class must be enabled for random generation.")
        if count <= 1:
            return "".join(random.choice(alphabet) for _ in range(max(1, length)))
        return ["".join(random.choice(alphabet) for _ in range(max(1, length))) for _ in range(count)]

    if kind in {"number", "int", "integer"}:
        values = [random.randint(min_value, max_value) for _ in range(count)]
        return values[0] if count <= 1 else values

    if kind in {"float", "decimal"}:
        values = [random.uniform(float(min_value), float(max_value)) for _ in range(count)]
        return values[0] if count <= 1 else values

    if kind in {"uuid", "guid"}:
        value = str(uuid.uuid4())
        return value if count <= 1 else [str(uuid.uuid4()) for _ in range(count)]

    if kind in {"name", "full_name"}:
        first = ["Ava", "Milo", "Nora", "Leo", "Sofia", "Noah", "Iris", "Eli"]
        last = ["Rivera", "Stone", "Bennett", "Nguyen", "Patel", "Cole", "Kim", "Morris"]
        value = f"{random.choice(first)} {random.choice(last)}"
        return value if count <= 1 else [f"{random.choice(first)} {random.choice(last)}" for _ in range(count)]

    if kind in {"email", "mail"}:
        local = ["alex", "river", "casey", "harper", "jordan", "morgan", "sam", "taylor"]
        domain = ["example.com", "local.dev", "fosseverything.app"]
        value = f"{random.choice(local)}.{random.randint(10, 99)}@{random.choice(domain)}"
        return value if count <= 1 else [f"{random.choice(local)}.{random.randint(10, 99)}@{random.choice(domain)}" for _ in range(count)]

    raise ValueError(f"Unsupported random generation type: {kind}")


def generate_ics(events: list[dict], calendar_name: str = "FOSSEverything") -> str:
    """Create a valid .ics calendar file payload from simple event dictionaries."""
    def escape_ics(value: str) -> str:
        return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    def to_ics_datetime(value: Any) -> str:
        if isinstance(value, str):
            candidate = value.strip()
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(candidate, fmt)
                    return dt.strftime("%Y%m%dT%H%M%S")
                except ValueError:
                    continue
            try:
                dt = datetime.fromisoformat(candidate)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            except ValueError:
                raise ValueError(f"Unsupported datetime value: {value!r}")
        if isinstance(value, datetime):
            dt = value
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        raise ValueError(f"Unsupported datetime value: {value!r}")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//FOSSEverything//Local Utility//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{escape_ics(calendar_name)}",
    ]

    if not events:
        lines.append("END:VCALENDAR")
        return "\n".join(lines) + "\n"

    for index, event in enumerate(events):
        summary = event.get("summary", "Untitled Event")
        start = event.get("start") or event.get("start_time")
        end = event.get("end") or event.get("end_time") or start
        description = event.get("description", "")
        location = event.get("location", "")
        uid = event.get("uid") or f"{index}-{uuid.uuid4()}@local"
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{to_ics_datetime(start)}",
            f"DTEND:{to_ics_datetime(end)}",
            f"SUMMARY:{escape_ics(str(summary))}",
        ])
        if description:
            lines.append(f"DESCRIPTION:{escape_ics(str(description))}")
        if location:
            lines.append(f"LOCATION:{escape_ics(str(location))}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\n".join(lines) + "\n"


def parse_ics(text: str) -> list[dict]:
    """Parse a .ics calendar payload back into simple event dictionaries.

    Handles the VEVENT subset produced by generate_ics() plus typical real-world
    exports: folded (continuation) lines, the common escape sequences, and both
    floating and UTC date-time forms.
    """
    def unescape_ics(value: str) -> str:
        return (
            value.replace("\\n", "\n").replace("\\N", "\n")
            .replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")
        )

    def from_ics_datetime(value: str) -> str:
        value = value.strip()
        for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y%m%d"):
            try:
                dt = datetime.strptime(value, fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S") if "T" in value else dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return value

    raw_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    unfolded: list[str] = []
    for raw_line in raw_lines:
        if raw_line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += raw_line[1:]
        elif raw_line:
            unfolded.append(raw_line)

    events: list[dict] = []
    current: dict | None = None
    for line in unfolded:
        if line == "BEGIN:VEVENT":
            current = {}
            continue
        if line == "END:VEVENT":
            if current is not None:
                events.append(current)
            current = None
            continue
        if current is None or ":" not in line:
            continue
        raw_key, value = line.split(":", 1)
        key = raw_key.split(";", 1)[0].upper()
        value = unescape_ics(value)
        if key == "SUMMARY":
            current["summary"] = value
        elif key == "DTSTART":
            current["start"] = from_ics_datetime(value)
        elif key == "DTEND":
            current["end"] = from_ics_datetime(value)
        elif key == "DESCRIPTION":
            current["description"] = value
        elif key == "LOCATION":
            current["location"] = value
        elif key == "UID":
            current["uid"] = value
    return events


def markdown_to_html(markdown_text: str) -> str:
    """Render a small subset of Markdown to HTML for live preview workflows."""
    if markdown_text is None:
        return ""

    def inline_format(value: str) -> str:
        value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
        value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
        value = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", value)
        return value

    lines = markdown_text.splitlines()
    html_lines = []
    in_code_block = False
    code_buffer = []
    in_ul = False
    in_ol = False
    in_quote = False

    def flush_list(tag: str) -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            html_lines.append("</ul>")
            in_ul = False
        if in_ol:
            html_lines.append("</ol>")
            in_ol = False

    for raw_line in lines:
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code_block:
                html_lines.append("<pre><code>" + html.escape("\n".join(code_buffer), quote=False) + "</code></pre>")
                code_buffer = []
                in_code_block = False
            else:
                flush_list("")
                in_code_block = True
            continue
        if in_code_block:
            code_buffer.append(line)
            continue
        if re.match(r"^#{1,6}\s+", line):
            flush_list("")
            match = re.match(r"^(#{1,6})\s+(.*)$", line)
            level = len(match.group(1))
            content = inline_format(html.escape(match.group(2)))
            html_lines.append(f"<h{level}>{content}</h{level}>")
            continue
        if re.match(r"^>\s*", line):
            flush_list("")
            if not in_quote:
                html_lines.append("<blockquote>")
                in_quote = True
            content = inline_format(html.escape(line[1:].strip()))
            html_lines.append(f"<p>{content}</p>")
            continue
        if in_quote:
            html_lines.append("</blockquote>")
            in_quote = False
        if re.match(r"^[-*]\s+", line):
            if not in_ul:
                html_lines.append("<ul>")
                in_ul = True
            html_lines.append(f"<li>{inline_format(html.escape(line[2:].strip()))}</li>")
            continue
        if re.match(r"^\d+\.\s+", line):
            if not in_ol:
                html_lines.append("<ol>")
                in_ol = True
            html_lines.append(f"<li>{inline_format(html.escape(re.sub(r'^\d+\.\s+', '', line)))}</li>")
            continue
        flush_list("")
        if line.strip():
            html_lines.append(f"<p>{inline_format(html.escape(line.strip()))}</p>")

    if in_ul:
        html_lines.append("</ul>")
    if in_ol:
        html_lines.append("</ol>")
    if in_quote:
        html_lines.append("</blockquote>")

    return "\n".join(html_lines)


def render_markdown_preview(markdown_text: str, *, text_color: str | None = None, panel_color: str | None = None, code_color: str | None = None, accent_color: str | None = None, border_color: str | None = None) -> str:
    """Return a complete HTML document suitable for a local preview pane."""
    body = markdown_to_html(markdown_text or "")
    text_color = text_color or "inherit"
    panel_color = panel_color or "transparent"
    code_color = code_color or "transparent"
    accent_color = accent_color or "currentColor"
    border_color = border_color or "currentColor"
    return (
        "<!doctype html>"
        "<html><head><meta charset=\"utf-8\"><style>"
        f"body{{font-family:Segoe UI,Arial,sans-serif;line-height:1.6;padding:24px;background:transparent;color:{text_color};}}"
        f"pre{{background:{panel_color};border-radius:8px;padding:12px;overflow:auto;}}"
        f"code{{background:{code_color};padding:2px 6px;border-radius:4px;}}"
        f"blockquote{{border-left:4px solid {accent_color};padding-left:12px;color:{text_color};}}"
        f"table{{border-collapse:collapse;width:100%;}}th,td{{border:1px solid {border_color};padding:8px;}}"
        "</style></head><body>" + body + "</body></html>"
    )


def diff_documents(left_text: str, right_text: str) -> dict:
    """Compare two text documents and return a summary plus unified diff output."""
    left_lines = left_text.splitlines()
    right_lines = right_text.splitlines()
    diff_lines = list(difflib.unified_diff(left_lines, right_lines, fromfile="left", tofile="right", lineterm=""))
    summary = {
        "added": 0,
        "removed": 0,
        "changed": bool(diff_lines),
    }
    for line in diff_lines:
        if line.startswith("+") and not line.startswith("+++"):
            summary["added"] += 1
        elif line.startswith("-") and not line.startswith("---"):
            summary["removed"] += 1
    return {
        "changed": summary["changed"],
        "summary": summary,
        "diff": "\n".join(diff_lines),
    }


def grammar_check_text(text: str) -> dict:
    """Run a lightweight local grammar/style check with actionable suggestions."""
    if text is None:
        text = ""
    issues = []
    stripped = text.strip()
    if not stripped:
        return {"valid": True, "issues": [], "score": 100, "summary": "No text to review."}

    if "  " in text:
        issues.append({"type": "double_space", "message": "Double spaces detected; replace them with a single space."})
    if re.search(r"\b(\w+)\s+\1\b", text, re.IGNORECASE):
        issues.append({"type": "repeated_word", "message": "Repeated word detected. Remove the duplicate."})
    if re.search(r"[.!][A-Za-z]", text):
        # Sentence spacing check: punctuation should usually be followed by a space.
        # This catches common punctuation mistakes without being overly strict.
        issues.append({"type": "sentence_spacing", "message": "Check sentence spacing after punctuation."})
    if re.search(r"\b[A-Z]{3,}\b", text) and "".join(text.split()):
        # Heuristic: a very long uppercase sequence usually suggests accidental caps lock.
        issues.append({"type": "caps_lock", "message": "Avoid long all-caps sequences unless intentionally formatting a title or acronym."})
    if re.search(r"\b(:it is|this is|that is)\s+[a-z]", text, re.IGNORECASE) and len(stripped.split()) > 7:
        issues.append({"type": "wordiness", "message": "Consider tightening wordy phrases for clearer writing."})

    score = max(0, 100 - (len(issues) * 12))
    summary = "Looks clean." if not issues else f"{len(issues)} possible grammar or style issue(s) found."
    return {"valid": not issues, "issues": issues, "score": score, "summary": summary}


_LANGUAGETOOL_INSTANCE: Any = None
_LANGUAGETOOL_UNAVAILABLE = False


def languagetool_backend_available() -> bool:
    """Return whether a local LanguageTool server backend can be started.

    LanguageTool runs as a local Java subprocess (never a cloud call); it is
    treated like the app's other optional local backends (Calibre, Ghostscript,
    Tesseract) and simply reports unavailable if Java or the jar can't start.
    """
    global _LANGUAGETOOL_INSTANCE, _LANGUAGETOOL_UNAVAILABLE
    if _LANGUAGETOOL_INSTANCE is not None:
        return True
    if _LANGUAGETOOL_UNAVAILABLE:
        return False
    try:
        _LANGUAGETOOL_INSTANCE = language_tool_python.LanguageTool("en-US")
        return True
    except Exception:
        _LANGUAGETOOL_UNAVAILABLE = True
        return False


def grammar_check_text_advanced(text: str) -> dict:
    """Run a full sentence-structure/style check via a local LanguageTool server.

    Returns the same shape as grammar_check_text (valid/issues/score/summary)
    plus "available": True, or {"available": False, "reason": ...} if the
    local LanguageTool backend can't be started - callers must fall back to
    grammar_check_text in that case rather than surface an error.
    """
    if not languagetool_backend_available():
        return {"available": False, "reason": "Local LanguageTool backend (requires Java) is not available."}

    if text is None:
        text = ""
    stripped = text.strip()
    if not stripped:
        return {"available": True, "valid": True, "issues": [], "score": 100, "summary": "No text to review."}

    matches = _LANGUAGETOOL_INSTANCE.check(text)
    issues = [
        {
            "type": match.category or match.ruleId,
            "message": match.message,
            "offset": match.offset,
            "length": match.errorLength,
            "replacements": list(match.replacements[:5]),
        }
        for match in matches
    ]
    score = max(0, 100 - (len(issues) * 8))
    summary = "Looks clean." if not issues else f"{len(issues)} possible grammar or style issue(s) found (LanguageTool)."
    return {"available": True, "valid": not issues, "issues": issues, "score": score, "summary": summary}


def generate_citation(entry: dict, style: str = "apa") -> str:
    """Generate a single citation entry for common book/article metadata."""
    style = (style or "apa").lower()
    authors = entry.get("authors") or entry.get("author") or []
    if isinstance(authors, str):
        authors = [authors]
    if not authors:
        authors = ["Unknown Author"]

    def format_author_list(items: list[str]) -> str:
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return f"{items[0]} & {items[1]}"
        return f"{items[0]}, et al."

    title = entry.get("title", "Untitled")
    year = entry.get("year") or entry.get("date") or "n.d."
    publisher = entry.get("publisher") or entry.get("journal") or entry.get("source") or ""
    doi = entry.get("doi") or ""
    url = entry.get("url") or ""

    if style == "mla":
        return f"{format_author_list(authors)}. \"{title}.\" {publisher or 'n.p.'}, {year}."
    if style == "chicago":
        return f"{format_author_list(authors)}. \"{title}.\" {publisher or 'n.p.'}, {year}."
    if style == "bibtex":
        author_key = " and ".join(a.replace(",", "") for a in authors[:2])
        return f"@misc{{{entry.get('key', author_key.lower().replace(' ', '_'))},\n  author = {{{' and '.join(authors)}}},\n  title = {{{title}}},\n  year = {{{year}}},\n  publisher = {{{publisher}}}\n}}"
    if style == "apa":
        if publisher:
            return f"{format_author_list(authors)}. ({year}). {title}. {publisher}."
        if doi:
            return f"{format_author_list(authors)}. ({year}). {title}. {doi}."
        if url:
            return f"{format_author_list(authors)}. ({year}). {title}. {url}."
        return f"{format_author_list(authors)}. ({year}). {title}."

    return f"{format_author_list(authors)} ({year}). {title}."


def generate_bibliography(entries: list[dict], style: str = "apa") -> str:
    """Generate a bibliography string from a list of entry dictionaries."""
    citations = [generate_citation(entry, style=style) for entry in entries]
    if style.lower() == "bibtex":
        return "\n\n".join(citations)
    return "\n".join(f"{idx + 1}. {citation}" for idx, citation in enumerate(citations))


def query_jsonpath(data: Any, path_expr: str) -> list[Any] | Any:
    """Evaluate JSONPath expressions: dot-notation, wildcards, array indexing, slicing,
    recursive descent, and simple filters."""
    expr = path_expr.strip()
    if not expr or expr == "$":
        return data

    if expr.startswith("$.."):
        expr = expr[1:]
    elif expr.startswith("$."):
        expr = expr[2:]
    elif expr.startswith("$"):
        expr = expr[1:]

    # Handle recursive descent: '..key'
    if expr.startswith(".."):
        target_key = expr[2:].strip()
        results = []

        def _walk(node: Any) -> None:
            if isinstance(node, dict):
                if target_key in node:
                    results.append(node[target_key])
                for v in node.values():
                    _walk(v)
            elif isinstance(node, list):
                for item in node:
                    _walk(item)

        _walk(data)
        return results

    # Tokenize path by dots/brackets, keeping bracketed sections intact (e.g. filter expressions).
    def _tokenize_path(expr: str) -> list[str]:
        tokens = []
        current = ""
        depth = 0
        i = 0
        while i < len(expr):
            ch = expr[i]
            if ch == "[":
                if current:
                    # Flush the current dot-segment as a key token
                    tokens.append(current)
                    current = ""
                # Read until matching ']'
                depth = 1
                bracket_content = "["
                i += 1
                while i < len(expr) and depth > 0:
                    c = expr[i]
                    if c == "[":
                        depth += 1
                    elif c == "]":
                        depth -= 1
                    bracket_content += c
                    i += 1
                tokens.append(bracket_content)
                continue
            elif ch == ".":
                if current:
                    tokens.append(current)
                    current = ""
                i += 1
                continue
            else:
                current += ch
            i += 1
        if current:
            tokens.append(current)
        return tokens

    raw_tokens = _tokenize_path(expr)
    current_nodes = [data]

    for token in raw_tokens:
        next_nodes = []
        if token.startswith("[") and token.endswith("]"):
            inner = token[1:-1].strip()
            # Check for filter expression: (@.field op val)
            filter_match = re.match(r'^\(\s*@\.(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)\s*\)$', inner)
            if filter_match:
                field, op, val_str = filter_match.groups()
                val_str = val_str.strip().strip("'\"")
                # Parse value if int/float/bool
                if val_str.lower() == "true":
                    comp_val = True
                elif val_str.lower() == "false":
                    comp_val = False
                elif val_str.isdigit():
                    comp_val = int(val_str)
                else:
                    try:
                        comp_val = float(val_str)
                    except ValueError:
                        comp_val = val_str

                for node in current_nodes:
                    if isinstance(node, list):
                        for item in node:
                            if isinstance(item, dict) and field in item:
                                item_val = item[field]
                                matched = False
                                try:
                                    if op == "==": matched = item_val == comp_val
                                    elif op == "!=": matched = item_val != comp_val
                                    elif op == ">": matched = item_val > comp_val
                                    elif op == "<": matched = item_val < comp_val
                                    elif op == ">=": matched = item_val >= comp_val
                                    elif op == "<=": matched = item_val <= comp_val
                                except TypeError:
                                    matched = False
                                if matched:
                                    next_nodes.append(item)
            elif inner == "*":
                for node in current_nodes:
                    if isinstance(node, list):
                        next_nodes.extend(node)
                    elif isinstance(node, dict):
                        next_nodes.extend(node.values())
            elif ":" in inner:
                # Slice: start:stop
                parts = inner.split(":")
                start = int(parts[0]) if parts[0] else None
                stop = int(parts[1]) if len(parts) > 1 and parts[1] else None
                for node in current_nodes:
                    if isinstance(node, list):
                        next_nodes.extend(node[slice(start, stop)])
            elif inner.lstrip("-").isdigit():
                idx = int(inner)
                for node in current_nodes:
                    if isinstance(node, list) and (-len(node) <= idx < len(node)):
                        next_nodes.append(node[idx])
            else:
                key = inner.strip("'\"")
                for node in current_nodes:
                    if isinstance(node, dict) and key in node:
                        next_nodes.append(node[key])
        elif token == "*":
            for node in current_nodes:
                if isinstance(node, dict):
                    next_nodes.extend(node.values())
                elif isinstance(node, list):
                    next_nodes.extend(node)
        else:
            for node in current_nodes:
                if isinstance(node, dict) and token in node:
                    next_nodes.append(node[token])
                elif isinstance(node, list):
                    for item in node:
                        if isinstance(item, dict) and token in item:
                            next_nodes.append(item[token])

        current_nodes = next_nodes

    # Unwrap a single scalar result (string/int/float/bool/None) for convenience,
    # but always return a list when the result is a collection of objects/lists.
    if len(current_nodes) == 1 and not isinstance(current_nodes[0], (dict, list)):
        return current_nodes[0]
    return current_nodes


def infer_json_schema(data: Any, title: str = "InferredSchema") -> dict:
    """Infer a standard JSON Schema (Draft 7) from a Python data object."""
    def _infer_type(obj: Any) -> dict:
        if obj is None:
            return {"type": "null"}
        elif isinstance(obj, bool):
            return {"type": "boolean"}
        elif isinstance(obj, int):
            return {"type": "integer"}
        elif isinstance(obj, float):
            return {"type": "number"}
        elif isinstance(obj, str):
            return {"type": "string"}
        elif isinstance(obj, list):
            if not obj:
                return {"type": "array", "items": {}}
            item_schemas = [_infer_type(item) for item in obj[:10]]
            # Combine property sets if array of objects
            if all(s.get("type") == "object" for s in item_schemas):
                merged_props = {}
                all_keys = set()
                for item in obj[:10]:
                    if isinstance(item, dict):
                        all_keys.update(item.keys())
                        for k, v in item.items():
                            if k not in merged_props:
                                merged_props[k] = _infer_type(v)
                return {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": merged_props,
                        "required": sorted(list(all_keys)),
                    }
                }
            return {"type": "array", "items": item_schemas[0]}
        elif isinstance(obj, dict):
            props = {k: _infer_type(v) for k, v in obj.items()}
            return {
                "type": "object",
                "properties": props,
                "required": sorted(list(obj.keys())),
            }
        return {"type": "string"}

    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": title,
        **_infer_type(data),
    }
    return schema


def _split_markdown_table_row(row: str) -> list[str]:
    """Split a markdown table row on pipe separators while preserving empty cells."""
    stripped = row.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def markdown_table_to_rows(table_text: str) -> list[dict[str, str]]:
    """Parse a pipe-delimited Markdown table into a list of dictionaries."""
    lines = [line.strip() for line in table_text.strip().splitlines() if line.strip()]
    if len(lines) < 3:
        return []
    headers = _split_markdown_table_row(lines[0])
    if not headers or all(not h for h in headers):
        return []
    rows = []
    for line in lines[2:]:
        if line.startswith("|") and line.endswith("|") and "-" in line:
            continue
        cells = _split_markdown_table_row(line)
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        elif len(cells) > len(headers):
            cells = cells[: len(headers)]
        rows.append({header: cells[idx] if idx < len(cells) else "" for idx, header in enumerate(headers)})
    return rows


def render_markdown_table(rows: list[dict] | list[list], headers: list[str] | None = None) -> str:
    """Render a table as Markdown from row dictionaries or row lists."""
    if not rows:
        return ""
    if isinstance(rows[0], dict):
        keys = headers or list(rows[0].keys())
        serial_rows = [
            [str(row.get(key, "")) for key in keys]
            for row in rows
        ]
    else:
        keys = headers or list(range(len(rows[0])))
        serial_rows = [[str(cell) for cell in row] for row in rows]
    if headers is not None:
        rendered_headers = list(headers)
    elif isinstance(rows[0], dict):
        rendered_headers = list(rows[0].keys())
    else:
        rendered_headers = [str(item) for item in keys]
    separator = ["---"] * len(rendered_headers)
    lines = [
        "| " + " | ".join(rendered_headers) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in serial_rows:
        padded = row + [""] * (len(rendered_headers) - len(row))
        lines.append("| " + " | ".join(padded) + " |")
    return "\n".join(lines)


def apply_schema_overrides(schema: dict, overrides: dict[str, str]) -> dict:
    """Override field types in a JSON Schema based on a name->type map."""
    if not isinstance(schema, dict):
        return schema

    updated = json.loads(json.dumps(schema))
    props = updated.get("properties", {})
    if isinstance(props, dict):
        for key, value in overrides.items():
            if key in props and isinstance(props[key], dict):
                props[key] = {**props[key], "type": value}
        updated["properties"] = props

    items = updated.get("items")
    if isinstance(items, dict):
        updated["items"] = apply_schema_overrides(items, overrides)

    return updated


def diff_json_schema(base_schema: dict, candidate_schema: dict, overrides: dict[str, str] | None = None) -> dict:
    """Compare two JSON Schema objects and report added, removed, and changed fields."""
    if overrides:
        base_schema = apply_schema_overrides(base_schema, overrides)
        candidate_schema = apply_schema_overrides(candidate_schema, overrides)

    base_props = base_schema.get("properties", {})
    candidate_props = candidate_schema.get("properties", {})
    all_keys = sorted(set(base_props) | set(candidate_props))

    added = []
    removed = []
    changed = []
    for key in all_keys:
        if key not in base_props:
            added.append({"field": key, "type": candidate_props[key].get("type", "unknown")})
        elif key not in candidate_props:
            removed.append({"field": key, "type": base_props[key].get("type", "unknown")})
        else:
            base_type = base_props[key].get("type", "unknown")
            candidate_type = candidate_props[key].get("type", "unknown")
            if base_type != candidate_type:
                changed.append({
                    "field": key,
                    "before": base_type,
                    "after": candidate_type,
                })

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "is_equivalent": not added and not removed and not changed,
    }


def clean_markdown_table(table_text: str, keep_empty_columns: bool = False, trim_whitespace: bool = True) -> str:
    """Normalize a Markdown table for cleaner notebook-style editing and exports."""
    if not table_text or not table_text.strip():
        return ""

    lines = [line.strip() for line in table_text.strip().splitlines() if line.strip()]
    if len(lines) < 2:
        return table_text.strip()

    parsed = []
    for line in lines:
        if line.startswith("|") and line.endswith("|"):
            line = line[1:-1]
        cells = [cell.strip() if trim_whitespace else cell for cell in line.split("|")]
        parsed.append(cells)

    header = parsed[0]
    body = parsed[1:]
    if body and all(cell.strip().replace("-", "") == "" for cell in body[0]):
        body = body[1:]

    if not keep_empty_columns:
        keep = [idx for idx in range(len(header)) if any(row[idx].strip() for row in body + [header])]
        header = [header[idx] for idx in keep]
        body = [[row[idx] for idx in keep] for row in body]

    if not header:
        return table_text.strip()

    rendered = ["| " + " | ".join(header) + " |"]
    rendered.append("| " + " | ".join(["---"] * len(header)) + " |")
    for row in body:
        padded = row + [""] * (len(header) - len(row))
        rendered.append("| " + " | ".join(str(value).strip() for value in padded) + " |")
    return "\n".join(rendered)


def normalize_markdown_table(table_text: str, keep_empty_columns: bool = False) -> str:
    """Parse a Markdown table, trim values, and emit a normalized version."""
    rows = markdown_table_to_rows(table_text)
    if not rows:
        return table_text.strip()
    headers = list(rows[0].keys())
    if not keep_empty_columns:
        headers = [header for header in headers if any(str(row.get(header, "")).strip() for row in rows)]
    normalized = [{header: str(row.get(header, "")).strip() for header in headers} for row in rows]
    return render_markdown_table(normalized, headers=headers)


def csv_to_markdown_table(csv_text: str, delimiter: str = ",", include_header: bool = True) -> str:
    """Convert CSV text into a Markdown table for easy review and documentation."""
    rows = list(csv.reader(io.StringIO(csv_text), delimiter=delimiter))
    if not rows:
        return ""
    if include_header:
        headers = rows[0]
        body = rows[1:]
    else:
        headers = [f"Column {idx + 1}" for idx in range(len(rows[0]))]
        body = rows
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in body:
        padded = row + [""] * (len(headers) - len(row))
        lines.append("| " + " | ".join(padded) + " |")
    return "\n".join(lines)


def validate_against_schema(data: Any, schema: dict) -> dict:
    """Perform a lightweight JSON-schema style validation preview for local data files."""
    errors: list[str] = []
    schema_type = schema.get("type")

    def _check_type(value: Any, expected: str, path: str) -> None:
        if expected == "object":
            if not isinstance(value, dict):
                errors.append(f"{path}: expected object")
                return
        elif expected == "array":
            if not isinstance(value, list):
                errors.append(f"{path}: expected array")
                return
        elif expected == "string":
            if not isinstance(value, str):
                errors.append(f"{path}: expected string")
        elif expected == "integer":
            if not isinstance(value, int) or isinstance(value, bool):
                errors.append(f"{path}: expected integer")
        elif expected == "number":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append(f"{path}: expected number")
        elif expected == "boolean":
            if not isinstance(value, bool):
                errors.append(f"{path}: expected boolean")
        elif expected == "null":
            if value is not None:
                errors.append(f"{path}: expected null")

    def _walk(value: Any, node: dict, path: str) -> None:
        if not isinstance(node, dict):
            return
        if "type" in node:
            _check_type(value, node["type"], path)
        if "enum" in node and value not in node["enum"]:
            errors.append(f"{path}: value not in enum {node['enum']}")
        if "properties" in node and isinstance(value, dict):
            props = node["properties"]
            for key, prop_schema in props.items():
                if key in value:
                    _walk(value[key], prop_schema, f"{path}.{key}")
                elif "required" in node and key in node["required"]:
                    errors.append(f"{path}.{key}: missing required property")
        if "items" in node and isinstance(value, list):
            item_schema = node["items"]
            for index, item in enumerate(value):
                _walk(item, item_schema, f"{path}[{index}]")
        if "minimum" in node and isinstance(value, (int, float)) and value < node["minimum"]:
            errors.append(f"{path}: below minimum {node['minimum']}")
        if "maximum" in node and isinstance(value, (int, float)) and value > node["maximum"]:
            errors.append(f"{path}: above maximum {node['maximum']}")

    if schema:
        _walk(data, schema, "$")
    if schema_type is not None and not isinstance(data, dict if schema_type == "object" else list if schema_type == "array" else str if schema_type == "string" else int if schema_type == "integer" else float if schema_type == "number" else bool if schema_type == "boolean" else type(None)):
        _check_type(data, schema_type, "$")

    return {"valid": not errors, "errors": errors, "issue_count": len(errors)}


def parse_cron_field(field: str, min_val: int, max_val: int) -> set[int]:
    """Parse one cron field (*, */N, ranges, lists, combinations) into a set of valid integers."""
    values: set[int] = set()
    for part in field.split(","):
        part = part.strip()
        if not part:
            raise ValueError(f"Empty cron field segment in {field!r}")
        step = 1
        if "/" in part:
            part, step_str = part.split("/", 1)
            try:
                step = int(step_str)
            except ValueError:
                raise ValueError(f"Invalid cron step value: {step_str!r}")
            if step <= 0:
                raise ValueError(f"Cron step must be positive: {step_str!r}")
        if part == "*":
            range_start, range_end = min_val, max_val
        elif "-" in part:
            start_str, end_str = part.split("-", 1)
            try:
                range_start, range_end = int(start_str), int(end_str)
            except ValueError:
                raise ValueError(f"Invalid cron range: {part!r}")
            if range_start > range_end:
                raise ValueError(f"Invalid cron range (start greater than end): {part!r}")
        else:
            try:
                range_start = range_end = int(part)
            except ValueError:
                raise ValueError(f"Invalid cron field value: {part!r}")
        if range_start < min_val or range_end > max_val:
            raise ValueError(f"Cron field value out of range [{min_val}, {max_val}]: {part!r}")
        values.update(range(range_start, range_end + 1, step))
    return values


_CRON_WEEKDAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
_CRON_MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _split_cron_expression(expression: str) -> tuple[str, str, str, str, str]:
    """Split a cron expression string into its 5 fields, validating the field count."""
    fields = expression.strip().split()
    if len(fields) != 5:
        raise ValueError(f"Cron expression must have 5 fields, got {len(fields)}: {expression!r}")
    return fields[0], fields[1], fields[2], fields[3], fields[4]


def describe_cron(expression: str) -> str:
    """Produce a short human-readable English description of a 5-field cron expression."""
    minute_f, hour_f, dom_f, month_f, dow_f = _split_cron_expression(expression)
    minutes = parse_cron_field(minute_f, 0, 59)
    hours = parse_cron_field(hour_f, 0, 23)
    doms = parse_cron_field(dom_f, 1, 31)
    months = parse_cron_field(month_f, 1, 12)
    dows = parse_cron_field(dow_f, 0, 6)

    if minute_f == "*" and hour_f == "*":
        time_part = "Every minute"
    elif minute_f.startswith("*/") and hour_f == "*":
        time_part = f"Every {minute_f[2:]} minutes"
    elif len(minutes) == 1 and len(hours) == 1:
        time_part = f"At {next(iter(hours)):02d}:{next(iter(minutes)):02d}"
    else:
        time_part = "At multiple times"

    if dow_f == "*" and dom_f == "*":
        day_part = "every day"
    elif dow_f != "*" and dom_f == "*":
        sorted_dows = sorted(dows)
        if sorted_dows == [1, 2, 3, 4, 5]:
            day_part = "Monday through Friday"
        elif sorted_dows == [0, 6]:
            day_part = "on weekends"
        else:
            day_part = "on " + ", ".join(_CRON_WEEKDAY_NAMES[d] for d in sorted_dows)
    elif dom_f != "*" and dow_f == "*":
        day_part = "on day " + ", ".join(str(d) for d in sorted(doms)) + " of the month"
    else:
        day_part = "on selected days"

    month_part = ""
    if month_f != "*":
        month_part = " in " + ", ".join(_CRON_MONTH_NAMES[m] for m in sorted(months))

    return f"{time_part}, {day_part}{month_part}"


def next_cron_runs(expression: str, count: int = 5, from_time: datetime | None = None) -> list[datetime]:
    """Compute the next N run times for a 5-field cron expression via brute-force minute stepping."""
    minute_f, hour_f, dom_f, month_f, dow_f = _split_cron_expression(expression)
    minutes = parse_cron_field(minute_f, 0, 59)
    hours = parse_cron_field(hour_f, 0, 23)
    doms = parse_cron_field(dom_f, 1, 31)
    months = parse_cron_field(month_f, 1, 12)
    dows = parse_cron_field(dow_f, 0, 6)

    start = from_time or datetime.now()
    candidate = start.replace(second=0, microsecond=0) + timedelta(minutes=1)
    safety_cutoff = candidate + timedelta(days=365 * 2)

    results: list[datetime] = []
    while candidate <= safety_cutoff:
        cron_weekday = (candidate.weekday() + 1) % 7
        if (
            candidate.minute in minutes
            and candidate.hour in hours
            and candidate.day in doms
            and candidate.month in months
            and cron_weekday in dows
        ):
            results.append(candidate)
            if len(results) >= count:
                return results
        candidate += timedelta(minutes=1)

    raise ValueError(f"No matching run times found within the safety window for: {expression!r}")

