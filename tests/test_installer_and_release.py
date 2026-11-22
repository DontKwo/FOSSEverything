"""Static checks that the installer script, release workflow, and README stay consistent."""
from __future__ import annotations

from pathlib import Path
import re

import pytest
import yaml

from app.system.install_options import INSTALL_SIDEBAR_MODES, INSTALL_STARTUP_VIEWS, INSTALL_THEMES
from app.system.shell_integration import FILE_FAMILIES
from scripts.update_readme_release_links import (
    END_MARKER,
    START_MARKER,
    render_release_block,
    update_readme_text,
)

ROOT = Path(__file__).resolve().parent.parent
ISS_TEXT = (ROOT / "installer" / "FOSSEverything.iss").read_text(encoding="utf-8")
LINUX_SH_TEXT = (ROOT / "installer" / "install-linux.sh").read_text(encoding="utf-8")
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


def extract_pascal_values(func_name: str) -> tuple[str, ...]:
    block = ISS_TEXT.split(f"function {func_name}")[1].split("end;")[0]
    return tuple(re.findall(r"^\s+\d+: Result := '([a-z0-9_]+)';", block, re.MULTILINE))


def test_every_file_family_has_a_component_and_registry_entries() -> None:
    assert len(FAMILY_COMPONENT_IDS) == len(FILE_FAMILIES)
    for component_id, (label, extensions) in zip(FAMILY_COMPONENT_IDS, FILE_FAMILIES):
        assert f'Name: "assoc\\{component_id}"' in ISS_TEXT, label
        assert registry_extensions(f"assoc\\{component_id}") == set(extensions), label


def test_wizard_theme_list_matches_app_themes() -> None:
    assert extract_pascal_values("ThemeIdAt") == INSTALL_THEMES


def test_wizard_sidebar_and_startup_views_match_app_options() -> None:
    assert extract_pascal_values("SidebarModeAt") == INSTALL_SIDEBAR_MODES
    assert extract_pascal_values("StartupViewAt") == INSTALL_STARTUP_VIEWS


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


def test_installer_exposes_core_customization_and_tasks() -> None:
    required_markers = (
        "[Types]",
        'Name: "standard"',
        "[Components]",
        "[Tasks]",
        'Name: "desktopicon"',
        'Name: "sendtomenu"',
        'Name: "addtopath"',
        'Name: "autostart"',
        "AddDirToUserPath",
        "RemoveDirFromUserPath",
        "--sidebar={code:GetSidebarMode}",
        "--startup-view={code:GetStartupView}",
        "CreateCustomPage",
        "DisableDirPage=no",
        "DisableProgramGroupPage=no",
        "AllowNoIcons=yes",
        "#ifndef MyAppVersion",
    )
    for needle in required_markers:
        assert needle in ISS_TEXT, needle


def test_linux_installer_exposes_sidebar_and_startup_view() -> None:
    assert "--sidebar" in LINUX_SH_TEXT
    assert "--startup-view" in LINUX_SH_TEXT


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
    assert "scripts/update_readme_release_links.py" in workflow_text


def test_readme_has_release_markers_and_links() -> None:
    assert START_MARKER in README_TEXT
    assert END_MARKER in README_TEXT
    assert "https://github.com/DontKwo/FOSSEverything/releases" in README_TEXT


@pytest.mark.parametrize("raw_version", ["0.1.27", "v0.1.28", "1.4.0"])
def test_render_release_block_includes_all_assets(raw_version: str) -> None:
    clean = raw_version.lstrip("v")
    block = render_release_block(raw_version, repo="Org/Repo")
    assert block.startswith(START_MARKER)
    assert block.endswith(END_MARKER)
    assert f"https://github.com/Org/Repo/releases/tag/v{clean}" in block
    for asset in RELEASE_ASSETS:
        assert f"https://github.com/Org/Repo/releases/latest/download/{asset}" in block
    for asset in RELEASE_ASSETS - {"SHA256SUMS.txt"}:
        assert f"https://github.com/Org/Repo/releases/download/v{clean}/{asset}" in block


def test_update_readme_text_preserves_surrounding_text() -> None:
    sample = f"Header\n\n{START_MARKER}\nold links\n{END_MARKER}\n\nFooter\n"
    updated = update_readme_text(sample, "2.0.1")
    assert updated.startswith("Header\n\n<!-- RELEASE-LINKS-START -->")
    assert updated.endswith("<!-- RELEASE-LINKS-END -->\n\nFooter\n")
    assert "old links" not in updated
    assert "releases/tag/v2.0.1" in updated


@pytest.mark.parametrize(
    ("bad_text", "bad_ver"),
    [
        ("no markers", "1.0.0"),
        (f"{START_MARKER}\nmissing end", "1.0.0"),
        (f"{START_MARKER}\n{END_MARKER}", ""),
        (f"{START_MARKER}\n{END_MARKER}", "v"),
    ],
)
def test_update_readme_text_rejects_invalid_inputs(bad_text: str, bad_ver: str) -> None:
    with pytest.raises(ValueError):
        update_readme_text(bad_text, bad_ver)
