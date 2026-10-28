import csv
import io
import json
import random
import secrets
from typing import Any

from app.features.data.ops import (
    clean_markdown_table,
    convert_data_format,
    convert_units,
    csv_to_markdown_table,
    describe_cron,
    diff_documents,
    diff_json_schema,
    format_css,
    format_javascript,
    format_json,
    format_sql,
    format_xml,
    format_yaml,
    generate_bibliography,
    generate_citation,
    generate_ics,
    generate_random_value,
    grammar_check_text,
    grammar_check_text_advanced,
    infer_json_schema,
    languagetool_backend_available,
    markdown_table_to_rows,
    minify_css,
    minify_javascript,
    minify_json,
    minify_sql,
    minify_xml,
    next_cron_runs,
    normalize_markdown_table,
    parse_ics,
    query_jsonpath,
    render_markdown_preview,
    validate_against_schema,
    validate_syntax,
)
from app.web.api.data_structure import inspect_data_structure
from app.web.api.hdf5_reader import export_hdf5_slice
from app.web.api.result import api_method, fail, ok, require


class DataApiMixin:
    @api_method
    def data_convert_format(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert data between JSON, YAML, XML, TOML, and CSV formats.
        require(params, "content", "source_format", "target_format")
        res = convert_data_format(
            str(params["content"]),
            str(params["source_format"]),
            str(params["target_format"]),
            indent=int(params.get("indent", 2)),
        )
        return ok(result=res)

    @api_method
    def convert_data_format(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for data format conversion.
        return self.data_convert_format(params)

    @api_method
    def data_format_code(self, params: dict[str, Any]) -> dict[str, Any]:
        # Format structured data or code string with clean indentation.
        require(params, "content", "language")
        content = str(params["content"])
        lang = str(params["language"]).lower()
        indent = int(params.get("indent", 2))

        if lang == "json":
            res = format_json(content, indent=indent)
        elif lang in ("js", "javascript"):
            res = format_javascript(content)
        elif lang == "css":
            res = format_css(content, indent=indent)
        elif lang == "sql":
            res = format_sql(content)
        elif lang == "xml":
            res = format_xml(content, indent=indent)
        elif lang == "yaml":
            res = format_yaml(content, indent=indent)
        else:
            return fail(f"Unsupported format language: {lang}", code="InvalidLanguage")
        return ok(result=res)

    @api_method
    def format_code(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for code formatting.
        return self.data_format_code(params)

    @api_method
    def format_json(self, params: dict[str, Any]) -> dict[str, Any]:
        # Format JSON text.
        require(params, "content")
        return ok(result=format_json(str(params["content"]), indent=int(params.get("indent", 2))))

    @api_method
    def format_sql(self, params: dict[str, Any]) -> dict[str, Any]:
        # Format SQL query string.
        require(params, "content")
        return ok(result=format_sql(str(params["content"])))

    @api_method
    def format_css(self, params: dict[str, Any]) -> dict[str, Any]:
        # Format CSS stylesheet string.
        require(params, "content")
        return ok(result=format_css(str(params["content"]), indent=int(params.get("indent", 2))))

    @api_method
    def format_javascript(self, params: dict[str, Any]) -> dict[str, Any]:
        # Format JavaScript source text.
        require(params, "content")
        return ok(result=format_javascript(str(params["content"])))

    @api_method
    def format_js(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for JavaScript formatting.
        return self.format_javascript(params)

    @api_method
    def format_xml(self, params: dict[str, Any]) -> dict[str, Any]:
        # Format XML document string.
        require(params, "content")
        return ok(result=format_xml(str(params["content"]), indent=int(params.get("indent", 2))))

    @api_method
    def format_yaml(self, params: dict[str, Any]) -> dict[str, Any]:
        # Format YAML document string.
        require(params, "content")
        return ok(result=format_yaml(str(params["content"]), indent=int(params.get("indent", 2))))

    @api_method
    def data_minify_code(self, params: dict[str, Any]) -> dict[str, Any]:
        # Minify structured code or data text.
        require(params, "content", "language")
        content = str(params["content"])
        lang = str(params["language"]).lower()

        if lang == "json":
            res = minify_json(content)
        elif lang in ("js", "javascript"):
            res = minify_javascript(content)
        elif lang == "css":
            res = minify_css(content)
        elif lang == "sql":
            res = minify_sql(content)
        elif lang == "xml":
            res = minify_xml(content)
        else:
            return fail(f"Unsupported minify language: {lang}", code="InvalidLanguage")
        return ok(result=res)

    @api_method
    def minify_json(self, params: dict[str, Any]) -> dict[str, Any]:
        # Minify JSON string.
        require(params, "content")
        return ok(result=minify_json(str(params["content"])))

    @api_method
    def data_validate_syntax(self, params: dict[str, Any]) -> dict[str, Any]:
        # Validate syntax of data formats (json, yaml, xml, toml, csv, sql).
        require(params, "content", "format")
        valid, msg, line = validate_syntax(str(params["content"]), str(params["format"]))
        return ok(valid=valid, message=msg, line=line)

    @api_method
    def validate_json(self, params: dict[str, Any]) -> dict[str, Any]:
        # Validate JSON syntax alias.
        valid, msg, line = validate_syntax(str(params.get("content", "")), "json")
        return ok(valid=valid, message=msg, line=line)

    @api_method
    def data_query_jsonpath(self, params: dict[str, Any]) -> dict[str, Any]:
        # Execute JSONPath expression against JSON content.
        require(params, "content", "path")
        matches = query_jsonpath(str(params["content"]), str(params["path"]))
        return ok(matches=matches)

    @api_method
    def query_jsonpath(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for JSONPath querying.
        return self.data_query_jsonpath(params)

    @api_method
    def data_infer_schema(self, params: dict[str, Any]) -> dict[str, Any]:
        # Infer JSON schema definition from JSON instance data.
        require(params, "content")
        schema = infer_json_schema(str(params["content"]), title=str(params.get("title", "Root")))
        return ok(schema=schema)

    @api_method
    def infer_json_schema(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for schema inference.
        return self.data_infer_schema(params)

    @api_method
    def data_convert_units(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert numerical values between physical measurement units.
        require(params, "value", "source_unit", "target_unit")
        res = convert_units(float(params["value"]), str(params["source_unit"]), str(params["target_unit"]))
        return ok(result=res)

    @api_method
    def data_cron_describe(self, params: dict[str, Any]) -> dict[str, Any]:
        # Describe cron expression in plain language and calculate upcoming executions.
        require(params, "expression")
        expr = str(params["expression"])
        desc = describe_cron(expr)
        count = int(params.get("count", 5))
        runs = next_cron_runs(expr, count=count)
        return ok(description=desc, upcoming_runs=runs)

    @api_method
    def data_ics_generate(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate iCalendar (ICS) event data string.
        require(params, "title", "start_time")
        ics_text = generate_ics(
            str(params["title"]),
            str(params["start_time"]),
            end_time=params.get("end_time"),
            description=str(params.get("description", "")),
            location=str(params.get("location", "")),
        )
        return ok(ics=ics_text)

    @api_method
    def data_ics_parse(self, params: dict[str, Any]) -> dict[str, Any]:
        # Parse events from iCalendar (ICS) formatted content.
        require(params, "content")
        events = parse_ics(str(params["content"]))
        return ok(events=events)

    @api_method
    def data_inspect_structure(self, params: dict[str, Any]) -> dict[str, Any]:
        # Analyze and explain hierarchical schema, keys, types, and values of a data file.
        res = inspect_data_structure(
            file_path=params.get("file_path"),
            content=params.get("content"),
            format_hint=params.get("format"),
        )
        return ok(**res)

    @api_method
    def data_hdf5_export_slice(self, params: dict[str, Any]) -> dict[str, Any]:
        # Extract sliced multidimensional data from HDF5 and export to CSV, JSON, or NPY.
        require(params, "file_path", "dataset_path", "output_path")
        file_path = str(params["file_path"])
        dataset_path = str(params["dataset_path"])
        output_path = str(params["output_path"])
        slice_spec = str(params.get("slice_spec", ":"))
        out_format = str(params.get("format", "csv"))
        res = export_hdf5_slice(file_path, dataset_path, slice_spec, output_path, out_format)
        return ok(**res)

    @api_method
    def data_random_value(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate random values with customizable length, count, ranges, and alphabets.
        require(params, "category")
        category = str(params["category"]).lower()
        length = int(params.get("length", 16))
        count = int(params.get("count", 1))
        min_val = int(params.get("min_value", 0))
        max_val = int(params.get("max_value", 100))
        inc_upper = bool(params.get("include_uppercase", True))
        inc_lower = bool(params.get("include_lowercase", True))
        inc_digits = bool(params.get("include_digits", True))
        inc_symbols = bool(params.get("include_symbols", False))
        custom_alphabet = params.get("custom_alphabet")

        if category == "hex":
            def make_hex() -> str:
                return secrets.token_hex((length + 1) // 2)[:length]
            values = [make_hex() for _ in range(count)]
            return ok(value=values[0] if count <= 1 else values, values=values, count=count)

        if category == "lorem":
            words = [
                "lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit",
                "sed", "do", "eiusmod", "tempor", "incididunt", "ut", "labore", "et", "dolore",
                "magna", "aliqua", "enim", "ad", "minim", "veniam", "quis", "nostrud",
                "exercitation", "ullamco", "laboris", "nisi", "aliquip", "ex", "ea", "commodo",
                "consequat", "duis", "aute", "irure", "in", "reprehenderit", "voluptate",
            ]
            def make_lorem() -> str:
                chosen = [random.choice(words) for _ in range(max(4, length))]
                return " ".join(chosen).capitalize() + "."
            values = [make_lorem() for _ in range(count)]
            return ok(value=values[0] if count <= 1 else values, values=values, count=count)

        random_val = generate_random_value(
            category,
            length=length,
            count=count,
            min_value=min_val,
            max_value=max_val,
            include_uppercase=inc_upper,
            include_lowercase=inc_lower,
            include_digits=inc_digits,
            include_symbols=inc_symbols,
            custom_alphabet=custom_alphabet,
        )
        values_list = random_val if isinstance(random_val, list) else [random_val]
        return ok(value=random_val, values=values_list, count=count)

    @api_method
    def data_grammar_check(self, params: dict[str, Any]) -> dict[str, Any]:
        # Check text grammar and spelling issues.
        require(params, "text")
        text = str(params["text"])
        advanced = bool(params.get("advanced", False))
        if advanced and languagetool_backend_available():
            matches = grammar_check_text_advanced(text, language=str(params.get("language", "en-US")))
        else:
            matches = grammar_check_text(text)
        return ok(matches=matches, lt_available=languagetool_backend_available())

    @api_method
    def data_generate_citation(self, params: dict[str, Any]) -> dict[str, Any]:
        # Format citation string for source metadata in specified style.
        require(params, "metadata", "style")
        cit = generate_citation(dict(params["metadata"]), str(params["style"]))
        return ok(citation=cit)

    @api_method
    def data_diff_documents(self, params: dict[str, Any]) -> dict[str, Any]:
        # Calculate structured diff between two document contents.
        require(params, "doc1", "doc2")
        diff_res = diff_documents(str(params["doc1"]), str(params["doc2"]))
        return ok(**diff_res)

    @api_method
    def data_render_preview(self, params: dict[str, Any]) -> dict[str, Any]:
        # Render markdown preview HTML with sanitization.
        require(params, "markdown")
        html_out = render_markdown_preview(str(params["markdown"]))
        return ok(html=html_out)

    @api_method
    def data_clean_table(self, params: dict[str, Any]) -> dict[str, Any]:
        # Clean markdown table with whitespace trimming and optional empty column removal.
        require(params, "content")
        tbl = clean_markdown_table(
            str(params["content"]),
            keep_empty_columns=bool(params.get("keep_empty_columns", False)),
            trim_whitespace=bool(params.get("trim_whitespace", True)),
        )
        return ok(result=tbl)

    @api_method
    def data_normalize_table(self, params: dict[str, Any]) -> dict[str, Any]:
        # Normalize markdown table column widths and padding.
        require(params, "content")
        tbl = normalize_markdown_table(
            str(params["content"]),
            keep_empty_columns=bool(params.get("keep_empty_columns", False)),
        )
        return ok(result=tbl)

    @api_method
    def data_csv_to_table(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert CSV or delimited content into Markdown table formatting.
        require(params, "content")
        raw_del = str(params.get("delimiter", ","))
        delimiter_map = {
            "tab": "\t", "\\t": "\t", "pipe": "|", "comma": ",",
            "semicolon": ";", "colon": ":", "space": " ",
        }
        delim = delimiter_map.get(raw_del.lower(), raw_del)
        tbl = csv_to_markdown_table(
            str(params["content"]),
            delimiter=delim,
            include_header=bool(params.get("include_header", True)),
        )
        return ok(result=tbl)

    @api_method
    def data_table_to_csv(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert Markdown table into delimited text with selectable delimiter and options.
        require(params, "content")
        raw_del = str(params.get("delimiter", ","))
        delimiter_map = {
            "tab": "\t", "\\t": "\t", "pipe": "|", "comma": ",",
            "semicolon": ";", "colon": ":", "space": " ",
        }
        delim = delimiter_map.get(raw_del.lower(), raw_del)
        include_header = bool(params.get("include_header", True))
        quote_char = str(params.get("quote_char", '"'))

        content = str(params["content"])
        rows = markdown_table_to_rows(content)
        if not rows:
            return ok(result="")
        headers = list(rows[0].keys())
        buf = io.StringIO()
        quoting = csv.QUOTE_MINIMAL if quote_char else csv.QUOTE_NONE
        writer = csv.writer(buf, delimiter=delim, quotechar=quote_char or '"', quoting=quoting)
        if include_header:
            writer.writerow(headers)
        for r in rows:
            writer.writerow([r.get(h, "") for h in headers])
        return ok(result=buf.getvalue())

    @api_method
    def data_change_delimiter(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert delimited text from one separator to another.
        require(params, "content", "from_delimiter", "to_delimiter")
        del_map = {
            "tab": "\t", "\\t": "\t", "pipe": "|", "comma": ",",
            "semicolon": ";", "colon": ":", "space": " ",
        }
        src_del = del_map.get(str(params["from_delimiter"]).lower(), str(params["from_delimiter"]))
        tgt_del = del_map.get(str(params["to_delimiter"]).lower(), str(params["to_delimiter"]))
        quote_char = str(params.get("quote_char", '"'))

        content = str(params["content"])
        reader = csv.reader(io.StringIO(content), delimiter=src_del, quotechar=quote_char or '"')
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=tgt_del, quotechar=quote_char or '"')
        for row in reader:
            writer.writerow(row)
        return ok(result=buf.getvalue())

    @api_method
    def data_table_to_rows(self, params: dict[str, Any]) -> dict[str, Any]:
        # Parse markdown table string into list of row dictionaries.
        require(params, "content")
        rows = markdown_table_to_rows(str(params["content"]))
        return ok(rows=rows)

    @api_method
    def data_diff_schema(self, params: dict[str, Any]) -> dict[str, Any]:
        # Diff two JSON schemas and return structural differences.
        require(params, "base_schema", "candidate_schema")
        base = json.loads(params["base_schema"]) if isinstance(params["base_schema"], str) else params["base_schema"]
        cand = json.loads(params["candidate_schema"]) if isinstance(params["candidate_schema"], str) else params["candidate_schema"]
        overrides = params.get("overrides")
        res = diff_json_schema(base, cand, overrides=overrides)
        return ok(**res)

    @api_method
    def data_validate_against_schema(self, params: dict[str, Any]) -> dict[str, Any]:
        # Validate data object against provided JSON schema.
        require(params, "content", "schema")
        data = json.loads(params["content"]) if isinstance(params["content"], str) else params["content"]
        schema = json.loads(params["schema"]) if isinstance(params["schema"], str) else params["schema"]
        res = validate_against_schema(data, schema)
        return ok(**res)

    @api_method
    def data_generate_bibliography(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate bibliography list for multiple metadata entries.
        require(params, "entries", "style")
        entries = list(params["entries"])
        style = str(params["style"])
        bib = generate_bibliography(entries, style=style)
        return ok(bibliography=bib)
