"""Test the workspace registry for routing files to appropriate workspaces."""
import unittest

from app.core.workspace_registry import WorkspaceDefinition, WorkspaceRegistry


class WorkspaceRegistryTests(unittest.TestCase):
    def test_registry_routes_common_file_types(self) -> None:
        registry = WorkspaceRegistry()
        registry.register(WorkspaceDefinition("pdf", "PDF Studio", "Documents", (".pdf",)))
        registry.register(WorkspaceDefinition("images", "Image Studio", "Images", (".png", ".jpg")))
        registry.register(WorkspaceDefinition("media", "Media Studio", "Media", (".mp3", ".mp4")))

        self.assertEqual(registry.find_for_path("docs/file.pdf").id, "pdf")
        self.assertEqual(registry.find_for_path("docs/pic.jpg").id, "images")
        self.assertEqual(registry.find_for_path("docs/song.mp3").id, "media")

    def test_registry_returns_none_for_unknown_extensions(self) -> None:
        registry = WorkspaceRegistry()
        self.assertIsNone(registry.find_for_path("docs/archive.unknown"))


if __name__ == "__main__":
    unittest.main()
