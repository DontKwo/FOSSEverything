"""Static checks that the installer script, release workflow, and README stay consistent."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from app.system.install_options import INSTALL_THEMES
from app.system.shell_integration import FILE_FAMILIES

ROOT = Path(__file__).resolve().parent.parent
ISS_TEXT = (ROOT / "installer" / "FOSSEverything.iss").read_text(encoding="utf-8")
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "build-exe.yml"
README_TEXT = (ROOT / "README.md").read_text(encoding="utf-8")

FAMILY_COMPONENT_IDS = ("pdf", "images", "media", "office", "data", "playlists", "model3d", "markdown")
RELEASE_ASSETS = {
    "FOSSEverything-Setup.exe",
    "FOSSEverything-Portable-win64.zip",
    "FOSSEverything-macos.dmg",
    "FOSSEverything-Portable-macos.zip",
    "FOSSEverything-Portable-linux64.tar.gz",
    "SHA256SUMS.txt",
}


def registry_extensions(component: str) -> set[str]:
    pattern = re.compile(
        r'Subkey: "Software\\Classes\\(\.[^\\]+)\\OpenWithProgids";[^\n]*Components: ' + re.escape(component) + r"\s*$",
        re.MULTILINE,
    )
    return set(pattern.findall(ISS_TEXT))


def test_every_file_family_has_a_component_and_registry_entries() -> None:
    assert len(FAMILY_COMPONENT_IDS) == len(FILE_FAMILIES)
    for component_id, (label, extensions) in zip(FAMILY_COMPONENT_IDS, FILE_FAMILIES):
        assert f'Name: "assoc\\{component_id}"' in ISS_TEXT, label
        assert registry_extensions(f"assoc\\{component_id}") == set(extensions), label


def test_wizard_theme_list_matches_app_themes() -> None:
    pascal_themes = re.findall(r"^\s+\d: Result := '([a-z_]+)';", ISS_TEXT.split("function ThemeIdAt")[1].split("end;")[0], re.MULTILINE)
    assert tuple(pascal_themes) == INSTALL_THEMES


def test_wizard_scales_are_within_app_range() -> None:
    block = ISS_TEXT.split("function ScaleValueAt")[1].split("end;")[0]
    values = [float(v) for v in re.findall(r"Result := '([0-9.]+)';", block)]
    assert values
    assert all(0.5 <= v <= 2.5 for v in values)


def test_installer_assets_and_files_exist() -> None:
    for name in re.findall(r"assets\\(wizard-[a-z@0-9-]+\.bmp)", ISS_TEXT):
        assert (ROOT / "installer" / "assets" / name).is_file(), name
    assert (ROOT / "assets" / "icon.ico").is_file()
    assert (ROOT / "LICENSE").is_file()


def test_installer_exposes_core_customization() -> None:
    for needle in ("[Types]", "[Components]", "[Tasks]", "CreateCustomPage", "DisableDirPage=no", "DisableProgramGroupPage=no", "AllowNoIcons=yes"):
        assert needle in ISS_TEXT, needle
    assert "#ifndef MyAppVersion" in ISS_TEXT


def load_workflow() -> dict[str, object]:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_workflow_builds_every_platform_and_publishes() -> None:
    jobs = load_workflow()["jobs"]
    assert {"version", "build-windows", "build-linux", "build-macos", "release"} <= set(jobs)
    assert jobs["release"]["permissions"]["contents"] == "write"
    assert set(jobs["release"]["needs"]) == {"version", "build-windows", "build-linux", "build-macos"}


def test_workflow_triggers_on_push_and_tags() -> None:
    triggers = load_workflow()["on"]
    assert "main" in triggers["push"]["branches"]
    assert "v*" in triggers["push"]["tags"]


def test_workflow_notes_and_readme_reference_only_produced_assets() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    readme_assets = set(re.findall(r"releases/latest/download/([A-Za-z0-9._-]+)", README_TEXT))
    assert readme_assets
    assert readme_assets <= RELEASE_ASSETS
    for asset in RELEASE_ASSETS - {"SHA256SUMS.txt"}:
        assert asset in workflow_text, asset
        assert asset in readme_assets, asset


def test_readme_links_to_releases_page() -> None:
    assert "https://github.com/DontKwo/FOSSEverything/releases" in README_TEXT
