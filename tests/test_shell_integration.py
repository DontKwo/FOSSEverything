"""Unit tests for shell integration and file routing."""
import unittest
from unittest.mock import patch, mock_open, MagicMock
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

    @patch("os.path.abspath")
    def test_resolve_windows_command(self, mock_abspath: MagicMock) -> None:
        mock_abspath.return_value = "C:\\dummy\\path.exe"
        cmd = shell_integration._resolve_windows_command(exe_path="C:\\dummy\\path.exe")
        self.assertTrue(cmd.endswith(' "%1"'))
        self.assertTrue(cmd.startswith('"C:\\dummy\\path.exe"'))

    @patch("os.makedirs")
    @patch("shutil.which")
    @patch("subprocess.run")
    def test_linux_registration_command_args(self, mock_run: MagicMock, mock_which: MagicMock, mock_makedirs: MagicMock) -> None:
        mock_which.return_value = None
        with patch("builtins.open", mock_open()) as mocked_file:
            shell_integration._register_linux(exe_path="/usr/bin/dummy")

            # Get the string written to the file
            write_calls = mocked_file().write.call_args_list
            written_content = "".join(call_arg[0][0] for call_arg in write_calls)

            self.assertIn("Exec=/usr/bin/dummy %F", written_content)

    @patch("os.makedirs")
    @patch("os.chmod")
    def test_macos_registration_command_args(self, mock_chmod: MagicMock, mock_makedirs: MagicMock) -> None:
        with patch("builtins.open", mock_open()) as mocked_file:
            shell_integration._register_macos(exe_path="/Applications/Dummy.app/Contents/MacOS/Dummy")

            write_calls = mocked_file().write.call_args_list
            written_content = "".join(call_arg[0][0] for call_arg in write_calls)

            self.assertIn('exec /Applications/Dummy.app/Contents/MacOS/Dummy "$@"', written_content)


if __name__ == "__main__":
    unittest.main()
