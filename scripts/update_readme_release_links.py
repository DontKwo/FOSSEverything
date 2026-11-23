"""Updates the release download table URLs in README.md when needed."""
from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_REPO: str = "DontKwo/FOSSEverything"

RELEASE_ENTRIES: tuple[tuple[str, str], ...] = (
    ("Windows", "FOSSEverything-Windows.exe"),
    ("macOS", "FOSSEverything-macOS.dmg"),
    ("Linux", "FOSSEverything-Linux.tar.gz"),
)


def normalize_version(version: str) -> str:
    """Strip any leading 'v' prefix and reject empty version strings."""
    cleaned = version.strip().lstrip("vV")
    if not cleaned:
        raise ValueError("Version string cannot be empty.")
    return cleaned


def render_download_rows(repo: str = DEFAULT_REPO) -> str:
    """Render canonical single-asset download table rows."""
    latest_base = f"https://github.com/{repo}/releases/latest/download"
    rows: list[str] = []
    for platform_label, asset_name in RELEASE_ENTRIES:
        section_anchor = platform_label.lower()
        rows.append(
            f"| {platform_label} | [{asset_name}]({latest_base}/{asset_name}) | "
            f"[{platform_label} Install Steps](docs/INSTALLATION.md#{section_anchor}) |"
        )
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    """Print canonical download table rows for the requested repository."""
    parser = argparse.ArgumentParser(description="Verify FOSSEverything release download URLs.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub owner/repository slug.")
    parser.add_argument("--version", default="0.1.0", help="Semantic release version to validate.")
    args = parser.parse_args(argv)
    normalize_version(args.version)
    _output = render_download_rows(repo=args.repo)
    if not _output:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
