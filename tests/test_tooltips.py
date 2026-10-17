"""Tests for the centralized tooltip dictionary and searchable help text."""
import unittest

from app.core.tooltips import TOOLTIP_DICTIONARY, get_tooltip_for, tooltip_search


class TooltipTests(unittest.TestCase):
    def test_dictionary_contains_common_action_labels(self) -> None:
        self.assertIn("Home", TOOLTIP_DICTIONARY)
        self.assertIn("Favorite", TOOLTIP_DICTIONARY)
        self.assertIn("Copy Image to Clipboard", TOOLTIP_DICTIONARY)
        self.assertIn("Open URL in Browser", TOOLTIP_DICTIONARY)

    def test_search_matches_tooltip_descriptions_and_keywords(self) -> None:
        home_matches = tooltip_search("home dashboard")
        self.assertIn("Home", [entry.label for entry in home_matches])
        self.assertEqual(get_tooltip_for("Home"), "Return to the Home dashboard and the local app launcher.")

        rotate_matches = tooltip_search("rotate image clockwise")
        self.assertIn("Rotate clockwise", [entry.label for entry in rotate_matches])
        self.assertEqual(get_tooltip_for("Move Up"), "Move the selected item upward in the current list or sequence.")

        qr_matches = tooltip_search("qr svg export")
        self.assertIn("Export Vector SVG", [entry.label for entry in qr_matches])


if __name__ == "__main__":
    unittest.main()
