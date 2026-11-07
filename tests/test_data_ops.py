"""Tests for Data Studio operations (JSON, YAML, XML, CSV)."""
import unittest
import json
from datetime import datetime
from app.features.data import ops as data_ops


class DataOpsTests(unittest.TestCase):
    def test_json_format_and_minify(self) -> None:
        raw = '{"b": 2, "a": [1, 2, 3]}'
        formatted = data_ops.format_json(raw, indent=2)
        self.assertIn("\n  \"a\": [", formatted)

        minified = data_ops.minify_json(formatted)
        self.assertEqual(minified, '{"b":2,"a":[1,2,3]}')

    def test_yaml_formatting(self) -> None:
        raw = "name: FOSSEverything\nversion: 1.0\nitems:\n  - pdf\n  - images\n"
        formatted = data_ops.format_yaml(raw, indent=2)
        self.assertIn("name: FOSSEverything", formatted)

    def test_syntax_validation(self) -> None:
        valid, msg, line = data_ops.validate_syntax('{"valid": true}', "json")
        self.assertTrue(valid)

        invalid, msg, line = data_ops.validate_syntax('{"invalid": true,}', "json")
        self.assertFalse(invalid)
        self.assertIsNotNone(line)

    def test_conversion_json_to_yaml_and_csv(self) -> None:
        json_text = '[{"name": "Alice", "role": "Admin"}, {"name": "Bob", "role": "User"}]'
        yaml_out = data_ops.convert_data_format(json_text, "json", "yaml")
        self.assertIn("name: Alice", yaml_out)

        csv_out = data_ops.convert_data_format(json_text, "json", "csv")
        self.assertIn("name,role", csv_out)

    def test_toml_ini_round_trip(self) -> None:
        payload = {"project": {"name": "demo", "version": "1.0.0"}, "enabled": True}
        json_text = json.dumps(payload)
        toml_text = data_ops.convert_data_format(json_text, "json", "toml")
        self.assertIn('name = "demo"', toml_text)

        ini_text = data_ops.convert_data_format(json_text, "json", "ini")
        self.assertIn("[project]", ini_text)

    def test_query_jsonpath(self) -> None:
        dataset = {
            "store": {
                "books": [
                    {"title": "Sayings of the Century", "price": 8.95},
                    {"title": "Sword of Honour", "price": 12.99},
                ],
                "owner": "John Doe"
            }
        }
        res1 = data_ops.query_jsonpath(dataset, "$.store.owner")
        self.assertEqual(res1, "John Doe")

        res2 = data_ops.query_jsonpath(dataset, "$.store.books[0].title")
        self.assertEqual(res2, "Sayings of the Century")

        res3 = data_ops.query_jsonpath(dataset, "$..price")
        self.assertEqual(res3, [8.95, 12.99])

        res4 = data_ops.query_jsonpath(dataset, "$.store.books[(@.price < 10)]")
        self.assertEqual(len(res4), 1)
        self.assertEqual(res4[0]["title"], "Sayings of the Century")

    def test_infer_json_schema(self) -> None:
        sample = {
            "id": 101,
            "name": "Widget",
            "price": 19.99,
            "in_stock": True,
            "tags": ["hardware", "tools"]
        }
        schema = data_ops.infer_json_schema(sample)
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["properties"]["id"]["type"], "integer")
        self.assertEqual(schema["properties"]["name"]["type"], "string")
        self.assertEqual(schema["properties"]["price"]["type"], "number")
        self.assertEqual(schema["properties"]["in_stock"]["type"], "boolean")
        self.assertEqual(schema["properties"]["tags"]["type"], "array")

    def test_markdown_table_roundtrip_and_schema_diff(self) -> None:
        table_text = "| name | role |\n| --- | --- |\n| Alice | Admin |\n| Bob | User |"
        rows = data_ops.markdown_table_to_rows(table_text)
        self.assertEqual(rows[0]["name"], "Alice")
        self.assertEqual(rows[1]["role"], "User")

        rendered = data_ops.render_markdown_table(rows)
        self.assertIn("| name |", rendered)

        base_schema = {"type": "object", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}}}
        new_schema = {"type": "object", "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "email": {"type": "string"}}}
        diff = data_ops.diff_json_schema(base_schema, new_schema, {"id": "integer"})
        self.assertTrue(diff["added"])  # email added
        self.assertTrue(diff["changed"] or diff["added"])

    def test_csv_to_markdown_and_schema_validation_preview(self) -> None:
        csv_text = "name,role\nAlice,Admin\nBob,User\n"
        markdown = data_ops.csv_to_markdown_table(csv_text)
        self.assertIn("| name | role |", markdown)
        self.assertIn("Alice", markdown)

        schema = {"type": "object", "properties": {"name": {"type": "string"}, "role": {"type": "string"}}, "required": ["name", "role"]}
        result = data_ops.validate_against_schema({"name": "Alice", "role": "Admin"}, schema)
        self.assertTrue(result["valid"])

        invalid = data_ops.validate_against_schema({"name": 42}, schema)
        self.assertFalse(invalid["valid"])

    def test_markdown_table_cleanup_helpers(self) -> None:
        raw = "| name | role |\n| --- | --- |\n| Alice | Admin |\n| Bob |  |\n|  | User |"
        cleaned = data_ops.clean_markdown_table(raw)
        self.assertIn("| name | role |", cleaned)
        self.assertIn("Alice", cleaned)
        self.assertIn("| Bob |", cleaned)

        normalized = data_ops.normalize_markdown_table(raw)
        self.assertIn("| name | role |", normalized)

    def test_unit_conversion_and_random_values(self) -> None:
        self.assertAlmostEqual(data_ops.convert_units(1, "km", "m", "length"), 1000.0)
        self.assertAlmostEqual(data_ops.convert_units(32, "f", "c", "temperature"), 0.0)

        value = data_ops.generate_random_value("password", 12, include_symbols=True)
        self.assertEqual(len(value), 12)

        numbers = data_ops.generate_random_value("number", 4, min_value=1, max_value=10, count=3)
        self.assertEqual(len(numbers), 3)

    def test_ics_generation(self) -> None:
        payload = data_ops.generate_ics([
            {
                "summary": "Team sync",
                "start": "2026-09-01T09:00:00",
                "end": "2026-09-01T10:00:00",
                "location": "HQ",
                "description": "Project planning",
            }
        ])
        self.assertIn("BEGIN:VCALENDAR", payload)
        self.assertIn("SUMMARY:Team sync", payload)
        self.assertIn("LOCATION:HQ", payload)

    def test_markdown_preview_rendering(self) -> None:
        html = data_ops.render_markdown_preview("# Heading\n\n- One\n- Two")
        self.assertIn("<h1>", html)
        self.assertIn("<ul>", html)
        self.assertIn("<li>", html)

    def test_document_diff_summary(self) -> None:
        diff = data_ops.diff_documents("alpha\nbeta", "alpha\ngamma")
        self.assertTrue(diff["changed"])
        self.assertGreater(diff["summary"]["added"], 0)
        self.assertGreater(diff["summary"]["removed"], 0)

    def test_grammar_and_citation_generation(self) -> None:
        review = data_ops.grammar_check_text("This has double  spaces and repeated repeated words.")
        self.assertFalse(review["valid"])
        self.assertGreater(len(review["issues"]), 0)

        citation = data_ops.generate_citation({
            "authors": ["Doe, Jane", "Smith, John"],
            "title": "Local-first workflows",
            "year": 2026,
            "publisher": "Acme Press",
        }, style="apa")
        self.assertIn("Local-first workflows", citation)

        bibliography = data_ops.generate_bibliography([
            {"authors": ["Riley, Sam"], "title": "Guide to Local Tools", "year": 2025, "publisher": "Open Press"}
        ], style="apa")
        self.assertIn("Guide to Local Tools", bibliography)

    def test_sql_format_and_minify(self) -> None:
        raw = "select id, name from users where id=1"
        formatted = data_ops.format_sql(raw)
        self.assertIn("SELECT", formatted)
        self.assertIn("\n", formatted)

        minified = data_ops.minify_sql("SELECT  *   FROM   users -- trailing comment\n")
        self.assertNotIn("--", minified)
        self.assertNotIn("  ", minified)

        valid, msg, _ = data_ops.validate_syntax("SELECT * FROM users", "sql")
        self.assertTrue(valid)

    def test_javascript_format_and_minify(self) -> None:
        raw = "function add(a,b){return a+b;}"
        formatted = data_ops.format_javascript(raw)
        self.assertIn("function add", formatted)
        self.assertIn("\n", formatted)

        commented = "// a comment\nfunction add(a, b) {\n  return a + b; // inline\n}\n"
        minified = data_ops.minify_javascript(commented)
        self.assertNotIn("//", minified)
        self.assertIn("function add", minified)

        preserved = data_ops.minify_javascript("const url = 'http://example.com';")
        self.assertIn("http://example.com", preserved)

    def test_css_format_and_minify(self) -> None:
        raw = "body{color:red;margin:0;}"
        formatted = data_ops.format_css(raw)
        self.assertIn("color: red", formatted)

        commented = "/* comment */\nbody {\n  color: red;\n  margin: 0;\n}\n"
        minified = data_ops.minify_css(commented)
        self.assertNotIn("/*", minified)
        self.assertEqual(minified, "body{color:red;margin:0}")

    def test_parse_cron_field(self) -> None:
        self.assertEqual(data_ops.parse_cron_field("*", 0, 4), {0, 1, 2, 3, 4})
        self.assertEqual(data_ops.parse_cron_field("1-3", 0, 10), {1, 2, 3})
        self.assertEqual(data_ops.parse_cron_field("1,3,5", 0, 10), {1, 3, 5})
        self.assertEqual(data_ops.parse_cron_field("*/15", 0, 59), {0, 15, 30, 45})
        self.assertEqual(data_ops.parse_cron_field("1-5,10,*/20", 0, 59), {1, 2, 3, 4, 5, 10, 0, 20, 40})

        with self.assertRaises(ValueError):
            data_ops.parse_cron_field("70", 0, 59)

    def test_describe_cron(self) -> None:
        self.assertEqual(data_ops.describe_cron("0 9 * * 1-5"), "At 09:00, Monday through Friday")
        self.assertEqual(data_ops.describe_cron("*/15 * * * *"), "Every 15 minutes, every day")
        self.assertEqual(data_ops.describe_cron("* * * * *"), "Every minute, every day")

        with self.assertRaises(ValueError):
            data_ops.describe_cron("0 9 * *")

    def test_next_cron_runs(self) -> None:
        start = datetime(2026, 9, 7, 8, 0, 0)
        runs = data_ops.next_cron_runs("0 9 * * 1-5", count=3, from_time=start)
        self.assertEqual(len(runs), 3)
        for run in runs:
            self.assertEqual(run.hour, 9)
            self.assertEqual(run.minute, 0)
            self.assertIn(run.weekday(), {0, 1, 2, 3, 4})
        self.assertLess(runs[0], runs[1])
        self.assertLess(runs[1], runs[2])
        self.assertGreater(runs[0], start)


if __name__ == "__main__":
    unittest.main()

