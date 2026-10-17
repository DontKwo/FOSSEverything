"""Unit tests for shell integration and file routing."""
import os
import tempfile
import unittest
from app.system import shell_integration


class TestShellIntegration(unittest.TestCase):
    def test_extension_classification(self) -> None:
        self.assertIn(".pdf", shell_integration.PDF_EXTENSIONS)
        self.assertIn(".png", shell_integration.IMAGE_EXTENSIONS)
        self.assertIn(".mp4", shell_integration.MEDIA_EXTENSIONS)
        self.assertIn(".json", shell_integration.DATA_EXTENSIONS)
        self.assertIn(".stl", shell_integration.MODEL3D_EXTENSIONS)
        self.assertIn(".step", shell_integration.MODEL3D_EXTENSIONS)

    def test_shell_registration_interface(self) -> None:
        # Function returns a tuple[bool, str] on any platform
        ok, msg = shell_integration.register_shell_context_menu()
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(msg, str)

        ok_un, msg_un = shell_integration.unregister_shell_context_menu()
        self.assertIsInstance(ok_un, bool)
        self.assertIsInstance(msg_un, str)


if __name__ == "__main__":
    unittest.main()
