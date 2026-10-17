"""Behavior tests for FOSSEverything's offline capability search."""
import unittest

from app.core.tool_registry import ToolDefinition, ToolRegistry


def _tool(identifier: str, title: str, category: str, keywords: tuple = (), description: str = "") -> ToolDefinition:
    return ToolDefinition(identifier, title, category, tuple(keywords), lambda: None, description)


class ToolRegistrySearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ToolRegistry()
        self.registry.register(_tool("pdf.merge", "Merge PDFs", "PDF", ("combine", "join", "append")))
        self.registry.register(_tool("pdf.compress", "Compress PDF", "PDF", ("shrink", "reduce size")))
        self.registry.register(_tool("image.crop", "Crop image", "Images", ("trim", "cut")))
        self.registry.register(_tool("image.resize", "Resize image", "Images", ("scale", "dimensions")))

    def ids(self, query: str) -> list[str]:
        return [match.tool.id for match in self.registry.search(query)]

    def test_synonym_query_finds_the_expected_tool(self) -> None:
        self.assertEqual(self.ids("combine"), ["pdf.merge"])
        self.assertEqual(self.ids("shrink pdf"), ["pdf.compress"])

    def test_category_filter_limits_results(self) -> None:
        self.assertEqual(self.ids("pdf:"), ["pdf.merge", "pdf.compress"])
        self.assertEqual(self.ids("images: resize"), ["image.resize"])

    def test_typo_tolerance_finds_a_tool(self) -> None:
        self.assertEqual(self.ids("reszie"), ["image.resize"])

    def test_all_words_must_match(self) -> None:
        self.assertEqual(self.ids("crop pdf"), [])


if __name__ == "__main__":
    unittest.main()
