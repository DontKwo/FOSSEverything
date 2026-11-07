"""One-click Windows installer builder: runs the PyInstaller build, then compiles the Inno Setup script."""
import os
import shutil
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISS_PATH = os.path.join(ROOT_DIR, "installer", "FOSSEverything.iss")
BUILD_EXE_SCRIPT = os.path.join(ROOT_DIR, "scripts", "build_executable.py")

ISCC_CANDIDATES = [
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",  # noqa: 26 (standard Inno Setup install location, used as a fallback lookup)
    r"C:\Program Files\Inno Setup 6\ISCC.exe",  # noqa: 26 (standard Inno Setup install location, used as a fallback lookup)
]


def find_iscc() -> str | None:
    found = shutil.which("ISCC.exe") or shutil.which("ISCC")
    if found:
        return found
    for candidate in ISCC_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate
    return None


def build() -> None:
    if sys.platform != "win32":
        print("The Inno Setup installer is Windows-only; skipping on this platform.")  # noqa: 25 (CLI status output, not debug)
        print("On macOS/Linux, use setup.sh instead (installs uv, syncs deps, runs the app).")  # noqa: 25 (CLI status output, not debug)
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
    res = subprocess.run([iscc, ISS_PATH], cwd=ROOT_DIR)
    if res.returncode != 0:
        print("Installer build FAILED. Review error messages above.")  # noqa: 25 (CLI status output, not debug)
        sys.exit(res.returncode)
    print("Installer build complete. Output is in installer\\Output\\FOSSEverything-Setup.exe")  # noqa: 25 (CLI status output, not debug)


if __name__ == "__main__":
    build()
