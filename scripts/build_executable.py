"""One-click standalone executable compilation script for FOSSEverything using PyInstaller."""
import os
import sys
import subprocess
import shutil

import imageio_ffmpeg

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRY_POINT = os.path.join(ROOT_DIR, "main.py")
DIST_DIR = os.path.join(ROOT_DIR, "dist")


def build(onefile: bool = False) -> None:
    print("=" * 60)  # noqa: 25 (CLI status output, not debug)
    print("   FOSSEverything - One-Click Standalone Executable Builder")  # noqa: 25 (CLI status output, not debug)
    print("=" * 60)  # noqa: 25 (CLI status output, not debug)
    print(f"Project Root: {ROOT_DIR}")  # noqa: 25 (CLI status output, not debug)
    print(f"Entry Point:  {ENTRY_POINT}")  # noqa: 25 (CLI status output, not debug)
    print()  # noqa: 25 (CLI status output, not debug)

    # Collect imageio-ffmpeg binaries if present
    extra_data = []
    try:
        ffmpeg_bin_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
        if os.path.exists(ffmpeg_bin_dir):
            extra_data.append(f"{ffmpeg_bin_dir}{os.pathsep}imageio_ffmpeg/binaries")
            print(f"Found bundled FFmpeg binaries at: {ffmpeg_bin_dir}")  # noqa: 25 (CLI status output, not debug)
    except Exception as exc:
        print(f"Notice: FFmpeg binary path detection: {exc}")  # noqa: 25 (CLI status output, not debug)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--name", "FOSSEverything",
        "--windowed",
        "--clean",
    ]

    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    # Bundles branding assets and embeds the exe icon so Explorer/taskbar/"Open
    # with" show FOSSEverything's icon instead of the generic Python one.
    assets_dir = os.path.join(ROOT_DIR, "assets")
    if os.path.exists(assets_dir):
        cmd.extend(["--add-data", f"{assets_dir}{os.pathsep}assets"])
    web_dir = os.path.join(ROOT_DIR, "app", "web")
    if os.path.exists(web_dir):
        cmd.extend(["--add-data", f"{web_dir}{os.pathsep}app/web"])
    icon_path = os.path.join(assets_dir, "icon.ico")
    if sys.platform == "win32" and os.path.isfile(icon_path):
        cmd.extend(["--icon", icon_path])

    # Add hidden imports
    hidden_imports = [
        "webview",
        "pythonnet",
        "clr_loader",
        "bottle",
        "proxy_tools",
        "pymupdf",
        "fitz",
        "PIL",
        "PIL.Image",
        "imageio_ffmpeg",
        "mutagen",
        "tinytag",
        "yaml",
        "cv2",
        "trimesh",
        "shapely",
        "mapbox_earcut",
    ]
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # The optional CAD backend ships native binaries PyInstaller can't auto-discover.
    try:
        import OCP  # noqa: 22
        cmd.extend(["--collect-all", "OCP"])
        print("Found optional CAD backend (OCP); collecting it into the build.")  # noqa: 25 (CLI status output, not debug)
    except ImportError:
        print("Optional CAD backend (OCP) not installed; build will support STL/OBJ/PLY only.")  # noqa: 25 (CLI status output, not debug)



    for d in extra_data:
        cmd.extend(["--add-data", d])

    cmd.append(ENTRY_POINT)

    print("Running PyInstaller command:")  # noqa: 25 (CLI status output, not debug)
    print(" ".join(cmd))  # noqa: 25 (CLI status output, not debug)
    print("-" * 60)  # noqa: 25 (CLI status output, not debug)

    res = subprocess.run(cmd, cwd=ROOT_DIR)
    if res.returncode == 0:
        print("=" * 60)  # noqa: 25 (CLI status output, not debug)
        if sys.platform == "win32":
            binary_name = "FOSSEverything.exe" if onefile else "FOSSEverything"
        elif sys.platform == "darwin":
            binary_name = "FOSSEverything.app" if not onefile else "FOSSEverything"
        else:
            binary_name = "FOSSEverything"
        out_location = os.path.join(DIST_DIR, binary_name)
        print(f"Standalone executable output located at:\n  {out_location}")  # noqa: 25 (CLI status output, not debug)
        print("=" * 60)  # noqa: 25 (CLI status output, not debug)
    else:
        print("=" * 60)  # noqa: 25 (CLI status output, not debug)
        print("BUILD FAILED. Review error messages above.")  # noqa: 25 (CLI status output, not debug)
        print("=" * 60)  # noqa: 25 (CLI status output, not debug)
        sys.exit(res.returncode)


if __name__ == "__main__":
    onefile_mode = "--onefile" in sys.argv
    build(onefile=onefile_mode)
