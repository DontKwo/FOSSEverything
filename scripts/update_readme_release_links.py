"""Updates the release download block in README.md between marker comments."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

START_MARKER = "<!-- RELEASE-LINKS-START -->"
END_MARKER = "<!-- RELEASE-LINKS-END -->"
DEFAULT_REPO = "DontKwo/FOSSEverything"

_RELEASE_ENTRIES: tuple[tuple[str, str, str], ...] = (
    (
        "**Windows**",
        "FOSSEverything-Setup.exe",
        "Setup wizard: folder, components, shortcuts, PATH, theme, startup view",
    ),
    (
        "**Windows**",
        "FOSSEverything-Portable-win64.zip",
        "Extract anywhere and run `FOSSEverything.exe`",
    ),
    (
        "**macOS**",
        "FOSSEverything-macos.dmg",
        "Open the DMG and drag the app to Applications",
    ),
    (
        "**macOS**",
        "FOSSEverything-Portable-macos.zip",
        "Extract and run `FOSSEverything.app`",
    ),
    (
        "**Linux**",
        "FOSSEverything-Portable-linux64.tar.gz",
        "Extract and run `./install.sh` (use `--help` for options)",
    ),
)


def normalize_version(version: str) -> str:
    # Strip any leading 'v' prefix and reject empty version strings.
    cleaned = version.strip().lstrip("vV")
    if not cleaned:
        raise ValueError("Version string cannot be empty.")
    return cleaned


def render_release_block(version: str, repo: str = DEFAULT_REPO) -> str:
    # Build the markdown section bounded by RELEASE-LINKS-START and RELEASE-LINKS-END.
    clean_ver = normalize_version(version)
    base_url = f"https://github.com/{repo}/releases"
    latest_base = f"{base_url}/latest/download"
    tag_base = f"{base_url}/download/v{clean_ver}"

    lines = [
        START_MARKER,
        (
            f"Latest release: **[v{clean_ver}]({base_url}/tag/v{clean_ver})** "
            f"([all releases]({base_url}) | "
            f"[SHA256SUMS.txt]({latest_base}/SHA256SUMS.txt))"
        ),
        "",
        "| Platform | Latest download | Versioned link | How to install |",
        "|---|---|---|---|",
    ]
    for platform_label, asset_name, install_note in _RELEASE_ENTRIES:
        lines.append(
            f"| {platform_label} | [{asset_name}]({latest_base}/{asset_name}) | "
            f"[v{clean_ver}]({tag_base}/{asset_name}) | {install_note} |"
        )
    lines.append(END_MARKER)
    return "\n".join(lines)


def update_readme_text(readme_text: str, version: str, repo: str = DEFAULT_REPO) -> str:
    # Replace the block between the start and end release link markers cleanly.
    start_idx = readme_text.find(START_MARKER)
    if start_idx == -1:
        raise ValueError(f"Missing start marker '{START_MARKER}' in README text.")
    end_idx = readme_text.find(END_MARKER, start_idx)
    if end_idx == -1:
        raise ValueError(f"Missing end marker '{END_MARKER}' in README text.")

    new_block = render_release_block(version, repo=repo)
    return readme_text[:start_idx] + new_block + readme_text[end_idx + len(END_MARKER) :]


def main(argv: list[str] | None = None) -> int:
    # Parse CLI arguments and overwrite README file in place with updated links.
    parser = argparse.ArgumentParser(description="Update release links in README.md.")
    parser.add_argument("--version", required=True, help="Release version without or with leading v.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub owner/repository slug.")
    parser.add_argument("--readme", default="README.md", help="Path to README file.")
    args = parser.parse_args(argv)

    readme_path = Path(args.readme)
    original = readme_path.read_text(encoding="utf-8")
    updated = update_readme_text(original, args.version, repo=args.repo)
    if updated != original:
        readme_path.write_text(updated, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
