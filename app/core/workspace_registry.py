"""Declarative workspace metadata for local tools and file routing."""
from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class WorkspaceDefinition:
    """A tool workspace with the file types it can accept."""

    id: str
    title: str
    category: str
    accepted_extensions: tuple[str, ...] = ()
    description: str = ""
    route_hint: str | None = None

    def matches(self, file_path: str) -> bool:
        if not file_path:
            return False
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.accepted_extensions or (self.route_hint and self.route_hint.lower() in file_path.lower())


class WorkspaceRegistry:
    """Map file extensions to the correct local workspace."""

    def __init__(self) -> None:
        self._workspaces: dict[str, WorkspaceDefinition] = {}

    def register(self, workspace: WorkspaceDefinition) -> None:
        self._workspaces[workspace.id] = workspace

    def all(self) -> list[WorkspaceDefinition]:
        return list(self._workspaces.values())

    def find_for_path(self, file_path: str) -> WorkspaceDefinition | None:
        for workspace in self.all():
            if workspace.matches(file_path):
                return workspace
        return None
