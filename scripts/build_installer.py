"""One-click Windows installer builder: runs the PyInstaller build, then compiles the Inno Setup script."""
import os
import shutil
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISS_PATH = os.path.join(ROOT_DIR, "installer", "FOSSEverything.iss")
BUILD_EXE_SCRIPT = os.path.join(ROOT_DIR, "scripts", "build_executable.py")

ISCC_CANDIDATES = [
    os.path.join(os.environ[env_name], "Inno Setup 6", "ISCC.exe")
    for env_name in ("ProgramFiles(x86)", "ProgramFiles")
    if env_name in os.environ
]


def find_iscc() -> str | None:
    found = shutil.which("ISCC.exe") or shutil.which("ISCC")
    if found:
        return found
    for candidate in ISCC_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate
    return None


def build(version: str | None = None) -> None:
    if sys.platform != "win32":
        print("The Inno Setup installer is Windows-only; skipping on this platform.")  # noqa: 25 (CLI status output, not debug)
        print("On macOS/Linux, use the release DMG or tarball (see README).")  # noqa: 25 (CLI status output, not debug)
        return

    print("Building the PyInstaller executable first...")  # noqa: 25 (CLI status output, not debug)
    res = subprocess.run([sys.executable, BUILD_EXE_SCRIPT], cwd=ROOT_DIR)
    if res.returncode != 0:
        sys.exit(res.returncode)

    iscc = find_iscc()
    if not iscc:
        print(  # noqa: 25 (CLI status output, not debug)
            "Inno Setup (ISCC.exe) was not found. Install it from "
            "https://jrsoftware.org/isinfo.php (free), then re-run this script."
        )
        sys.exit(1)

    print(f"Compiling installer with: {iscc}")  # noqa: 25 (CLI status output, not debug)
    iscc_cmd = [iscc] + ([f"/DMyAppVersion={version}"] if version else []) + [ISS_PATH]
    res = subprocess.run(iscc_cmd, cwd=ROOT_DIR)
    if res.returncode != 0:
        print("Installer build FAILED. Review error messages above.")  # noqa: 25 (CLI status output, not debug)
        sys.exit(res.returncode)
    print("Installer build complete. Output is in installer\\Output\\FOSSEverything-Setup.exe")  # noqa: 25 (CLI status output, not debug)


if __name__ == "__main__":
    version_arg = next((arg.split("=", 1)[1] for arg in sys.argv[1:] if arg.startswith("--version=")), None)
    build(version=version_arg)
