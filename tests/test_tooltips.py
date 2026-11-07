"""Tests for the centralized tooltip dictionary and searchable help text."""

import unittest

from app.core.tooltips import (
    TOOLTIP_DICTIONARY,
    copy_hex_tooltip,
    get_tooltip_for,
    keywords_tooltip,
    tooltip_search,
)


class TooltipTests(unittest.TestCase):
    def test_dictionary_contains_common_action_labels(self) -> None:
        self.assertIn("Home", TOOLTIP_DICTIONARY)
        self.assertIn("Favorite", TOOLTIP_DICTIONARY)
        self.assertIn("Copy Image to Clipboard", TOOLTIP_DICTIONARY)
        self.assertIn("Open URL in Browser", TOOLTIP_DICTIONARY)

    def test_search_matches_tooltip_descriptions_and_keywords(self) -> None:
        home_matches = tooltip_search("home dashboard")
        self.assertIn("Home", [entry.label for entry in home_matches])
        self.assertEqual(
            get_tooltip_for("Home"),
            "Return to the Home dashboard and the local app launcher.",
        )

        rotate_matches = tooltip_search("rotate image clockwise")
        self.assertIn("Rotate clockwise", [entry.label for entry in rotate_matches])
        self.assertEqual(
            get_tooltip_for("Move Up"),
            "Move the selected item upward in the current list or sequence.",
        )

        qr_matches = tooltip_search("qr svg export")
        self.assertIn("Export Vector SVG", [entry.label for entry in qr_matches])

    def test_dictionary_keys_match_entry_keys(self) -> None:
        for dict_key, entry in TOOLTIP_DICTIONARY.items():
            self.assertEqual(dict_key, entry.key)

    def test_dictionary_labels_match_keys_mostly(self) -> None:
        for dict_key, entry in TOOLTIP_DICTIONARY.items():
            if dict_key == "Tray icon":
                self.assertEqual(entry.label, "FOSSEverything")
            else:
                self.assertEqual(dict_key, entry.label)

    def test_entry_properties(self) -> None:
        entry = TOOLTIP_DICTIONARY["Home"]
        self.assertEqual(entry.tooltip, entry.description)
        self.assertIn("home", entry.search_text)
        self.assertIn("dashboard", entry.search_text)

    def test_get_tooltip_for_fallback(self) -> None:
        fallback = get_tooltip_for("NonexistentTool")
        self.assertEqual(fallback, "Use NonexistentTool to access this feature.")

    def test_keywords_tooltip_formatting(self) -> None:
        result = keywords_tooltip(("test", "keyword"))
        self.assertEqual(result, "Keywords: test, keyword")

    def test_copy_hex_tooltip_formatting(self) -> None:
        result = copy_hex_tooltip("#ff0000")
        self.assertEqual(result, "Click to copy: #ff0000")


if __name__ == "__main__":
    unittest.main()
