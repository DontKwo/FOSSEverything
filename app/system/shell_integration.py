"""Cross-platform shell integration, context menu registration, and file routing."""
from __future__ import annotations

import ctypes
import json
import mimetypes
import os
import sys
import shutil
import subprocess
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QTimer
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

if TYPE_CHECKING:
    from app.ui.main_window import MainWindow

APP_NAME = "FOSSEverything"
APP_DESCRIPTION = "FOSSEverything - Local Desktop Power Tool"
IPC_SERVER_NAME = "FOSSEverything-ipc-v1"

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def app_icon_path() -> str:
    """Absolute path to the app's .ico asset, valid both from source and in a frozen build."""
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), "assets", "icon.ico")
    return os.path.join(_PROJECT_ROOT, "assets", "icon.ico")

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".gif", ".ico", ".svg"}
PDF_EXTENSIONS = {".pdf"}
MEDIA_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".wmv", ".m4v", ".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma", ".opus"}
DATA_EXTENSIONS = {".json", ".yaml", ".yml", ".csv", ".xml", ".tsv"}
OFFICE_EXTENSIONS = {".docx", ".pptx", ".xlsx", ".odt", ".ods", ".odp", ".docm", ".pptm", ".xlsm"}
PLAYLIST_EXTENSIONS = {".m3u8", ".m3u"}
MODEL3D_EXTENSIONS = {".stl", ".obj", ".ply", ".step", ".stp", ".iges", ".igs"}
MARKDOWN_EXTENSIONS = {".md", ".markdown"}

FILE_FAMILIES: tuple[tuple[str, frozenset[str]], ...] = (
    ("PDF documents", frozenset(PDF_EXTENSIONS)),
    ("Images", frozenset(IMAGE_EXTENSIONS)),
    ("Audio && video", frozenset(MEDIA_EXTENSIONS)),
    ("Office documents", frozenset(OFFICE_EXTENSIONS)),
    ("Data files", frozenset(DATA_EXTENSIONS)),
    ("Playlists", frozenset(PLAYLIST_EXTENSIONS)),
    ("3D models", frozenset(MODEL3D_EXTENSIONS)),
    ("Markdown documents", frozenset(MARKDOWN_EXTENSIONS)),
)


# Mirrors MainWindow._TAB_MAKERS' import targets, so a background thread can
# warm the module cache for the workspace a routed file will need.
WORKSPACE_MODULE: dict[str, str] = {
    "pdf": "app.features.pdf.tab", "images": "app.features.image.tab",
    "media": "app.features.media.tab", "markdown": "app.features.markdown.tab",
    "word_counter": "app.features.word_counter.tab", "data": "app.features.data.tab",
    "model3d": "app.features.model3d.tab", "ocr": "app.features.ocr.tab",
    "hash": "app.features.hash.tab", "converter": "app.features.converter.tab",
    "playlist": "app.features.playlist.tab",
}


def resolve_workspace_id(file_path: str, force_mode: str | None = None) -> str:
    """Which workspace `route_file` would switch to for this file, without building it."""
    ext = os.path.splitext(file_path)[1].lower()
    if force_mode == "ocr" or ext == ".ocr":
        return "ocr"
    if force_mode == "hash":
        return "hash"
    if ext in PDF_EXTENSIONS:
        return "pdf"
    if ext in IMAGE_EXTENSIONS:
        return "images"
    if ext in MEDIA_EXTENSIONS:
        return "media"
    if ext in MARKDOWN_EXTENSIONS:
        return "markdown"
    if ext in OFFICE_EXTENSIONS:
        return "word_counter"
    if ext in PLAYLIST_EXTENSIONS:
        return "playlist"
    if ext in DATA_EXTENSIONS:
        return "data"
    if ext in MODEL3D_EXTENSIONS:
        return "model3d"
    return "converter"


def preload_workspace_module_in_background(file_path: str, force_mode: str | None = None) -> None:
    """Import the tab module a routed file will need on a background thread, so its
    (often heavy, e.g. numpy/pymupdf) import cost overlaps with window construction
    instead of running serially after the window is already shown."""
    import importlib
    import threading

    module_name = WORKSPACE_MODULE.get(resolve_workspace_id(file_path, force_mode))
    if module_name is None:
        return
    threading.Thread(target=importlib.import_module, args=(module_name,), daemon=True).start()


def _defer_load(tab: Any, file_path: str) -> None:
    """Load the file on the next event-loop tick instead of blocking the paint
    that follows the workspace switch that just happened."""
    if hasattr(tab, "load_file"):
        QTimer.singleShot(0, lambda: tab.load_file(file_path))


def route_file(window: MainWindow, file_path: str, force_mode: str | None = None) -> bool:
    """Intelligently route a file passed via CLI / file association to the correct workspace."""
    if not os.path.exists(file_path):
        return False

    ext = os.path.splitext(file_path)[1].lower()

    if force_mode == "ocr" or ext == ".ocr":
        window.open_workspace("ocr")
        _defer_load(window.ocr_tab, file_path)
        return True

    if force_mode == "hash":
        window.open_workspace("hash")
        _defer_load(window.hash_tab, file_path)
        return True

    if ext in PDF_EXTENSIONS:
        window.open_workspace("pdf")
        _defer_load(window.pdf_tab, file_path)
        return True

    if ext in IMAGE_EXTENSIONS:
        window.open_workspace("images")
        _defer_load(window.image_tab, file_path)
        return True

    if ext in MEDIA_EXTENSIONS:
        window.open_workspace("media")
        _defer_load(window.media_tab, file_path)
        return True

    if ext in MARKDOWN_EXTENSIONS:
        window.open_workspace("markdown")
        _defer_load(window.markdown_tab, file_path)
        return True

    if ext in OFFICE_EXTENSIONS:
        window.open_workspace("word_counter")
        _defer_load(window.word_counter_tab, file_path)
        return True

    if ext in PLAYLIST_EXTENSIONS:
        window.open_workspace("playlist")
        return True

    if ext in DATA_EXTENSIONS:
        window.open_workspace("data")
        _defer_load(window.data_tab, file_path)
        return True

    if ext in MODEL3D_EXTENSIONS:
        window.open_workspace("model3d")
        _defer_load(window.model3d_tab, file_path)
        return True

    window.open_workspace("converter")
    _defer_load(window.converter_tab, file_path)
    return True


# ─── Single-instance IPC ──────────────────────────────────────────────────────
def try_forward_to_running_instance(file_path: str | None, force_mode: str | None = None) -> bool:
    """Hand a launch request to an already-running instance instead of cold-starting a new one."""
    socket = QLocalSocket()
    socket.connectToServer(IPC_SERVER_NAME)
    if not socket.waitForConnected(200):
        return False
    payload = json.dumps({"file": file_path, "force_mode": force_mode}).encode("utf-8")
    socket.write(payload)
    socket.waitForBytesWritten(500)
    socket.disconnectFromServer()
    return True


def start_ipc_server(window: MainWindow) -> QLocalServer:
    """Listen for launch requests from newly started processes and route them into this warm instance."""
    QLocalServer.removeServer(IPC_SERVER_NAME)
    server = QLocalServer()
    server.listen(IPC_SERVER_NAME)

    def _on_new_connection() -> None:
        connection = server.nextPendingConnection()
        if connection is None:
            return
        if connection.waitForReadyRead(500):
            try:
                data = json.loads(bytes(connection.readAll()).decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                data = {}
            window.show()
            window.raise_()
            window.activateWindow()
            file_path = data.get("file")
            if file_path:
                route_file(window, file_path, force_mode=data.get("force_mode"))
        connection.disconnectFromServer()

    server.newConnection.connect(_on_new_connection)
    return server


# ─── Cross-Platform Shell Registration ───────────────────────────────────────
def register_shell_context_menu(exe_path: str | None = None) -> tuple[bool, str]:
    """Register 'Open in OmniDeck' in the operating system's file manager context menu."""
    if sys.platform == "win32":
        return _register_windows(exe_path)
    elif sys.platform.startswith("linux"):
        return _register_linux(exe_path)
    elif sys.platform == "darwin":
        return _register_macos(exe_path)
    return False, f"Unsupported operating system: {sys.platform}"


def ensure_open_with_candidacy() -> tuple[bool, str]:
    """Silently register FOSSEverything as an 'Open with' candidate for its file types.

    Unlike set_default_for_extensions(), this never opens an OS picker or requires
    user confirmation, so it's safe to call on every startup (idempotent, HKCU-only).
    """
    if sys.platform == "win32":
        return _register_app_capabilities_windows()
    if sys.platform.startswith("linux"):
        return _register_linux()
    return True, f"No automatic 'Open with' registration needed on {sys.platform}."


def unregister_shell_context_menu() -> tuple[bool, str]:
    """Remove 'Open in OmniDeck' from the operating system's file manager context menu."""
    if sys.platform == "win32":
        return _unregister_windows()
    elif sys.platform.startswith("linux"):
        return _unregister_linux()
    elif sys.platform == "darwin":
        return _unregister_macos()
    return False, f"Unsupported operating system: {sys.platform}"


# ─── Windows ─────────────────────────────────────────────────────────────────
def _resolve_windows_command(exe_path: str | None = None) -> str:
    if not exe_path:
        if getattr(sys, "frozen", False):
            exe_path = sys.executable
        else:
            # python.exe allocates a visible console window; pythonw.exe (same install,
            # windowless) is what file-association launches should use instead.
            python_exe = sys.executable
            pythonw = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
            if os.path.exists(pythonw):
                python_exe = pythonw
            exe_path = f'"{python_exe}" "{os.path.abspath(sys.argv[0])}"'
    else:
        exe_path = f'"{os.path.abspath(exe_path)}"'
    return f'{exe_path} "%1"'


def _progid_for_extension(ext: str) -> str:
    return f"FOSSEverything{ext}"


def _register_windows(exe_path: str | None = None) -> tuple[bool, str]:
    try:
        import winreg  # noqa: 22
    except ImportError:
        return False, "winreg module not available."

    command_str = _resolve_windows_command(exe_path)

    try:
        key_path = r"Software\Classes\*\shell\FOSSEverything"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f"Open in {APP_NAME}")
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, app_icon_path())

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path + r"\command") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command_str)

        dir_key_path = r"Software\Classes\Directory\shell\FOSSEverything"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, dir_key_path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f"Open in {APP_NAME}")
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, app_icon_path())

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, dir_key_path + r"\command") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command_str)

        return True, "Successfully registered 'Open in FOSSEverything' in Windows right-click context menu!"
    except Exception as exc:
        return False, f"Failed to register context menu: {exc}"


def _unregister_windows() -> tuple[bool, str]:
    try:
        import winreg  # noqa: 22
    except ImportError:
        return False, "winreg module not available."

    def delete_sub_key(root: Any, sub_key: str) -> None:
        try:
            with winreg.OpenKey(root, sub_key, 0, winreg.KEY_ALL_ACCESS) as key:
                while True:
                    try:
                        child = winreg.EnumKey(key, 0)
                        delete_sub_key(key, child)
                    except OSError:
                        break
            winreg.DeleteKey(root, sub_key)
        except FileNotFoundError:  # noqa: 10 (best-effort cleanup; key already gone, nothing to do)
            pass

    try:
        delete_sub_key(winreg.HKEY_CURRENT_USER, r"Software\Classes\*\shell\FOSSEverything")
        delete_sub_key(winreg.HKEY_CURRENT_USER, r"Software\Classes\Directory\shell\FOSSEverything")
        return True, "Successfully removed 'Open in FOSSEverything' from Windows context menu."
    except Exception as exc:
        return False, f"Failed to unregister context menu: {exc}"


# ─── Default-app registration ────────────────────────────────────────────────
def manual_association_instructions(extensions: Iterable[str]) -> str:
    ext_list = ", ".join(sorted(extensions))
    if sys.platform == "darwin":
        return (
            f"To set FOSSEverything as the default app for {ext_list} manually on macOS:\n"
            "1. Right-click (or Control-click) a file with that extension in Finder.\n"
            "2. Choose \"Get Info\".\n"
            "3. Under \"Open with\", select FOSSEverything.\n"
            "4. Click \"Change All...\" to apply it to every file of that type."
        )
    if sys.platform.startswith("linux"):
        return (
            f"To set FOSSEverything as the default app for {ext_list} manually on Linux:\n"
            "1. Right-click a file with that extension in your file manager.\n"
            "2. Choose \"Open With\" -> \"Other Application\" (wording varies by desktop environment).\n"
            "3. Select FOSSEverything and enable \"Always use this application\".\n\n"
            "Or, per file type: xdg-mime default fosseverything.desktop <mime-type>"
        )
    return (
        f"To set FOSSEverything as the default app for {ext_list} manually on Windows:\n"
        "1. Right-click a file with that extension in File Explorer.\n"
        "2. Choose \"Open with\" -> \"Choose another app\".\n"
        "3. Select FOSSEverything (click \"More apps\" if it's not shown).\n"
        "4. Check \"Always use this app\".\n"
        "5. Click OK.\n\n"
        "Or: Settings -> Apps -> Default apps -> search \"FOSSEverything\" -> set it for each file type."
    )


def is_default_for_extension(ext: str) -> bool:
    """Report whether FOSSEverything is the current OS default for this extension (read-only)."""
    if sys.platform == "win32":
        return _is_default_windows(ext)
    if sys.platform.startswith("linux"):
        return _is_default_linux(ext)
    return False


def _is_default_windows(ext: str) -> bool:
    try:
        import winreg  # noqa: 22
    except ImportError:
        return False
    try:
        key_path = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{ext}\UserChoice"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            progid, _ = winreg.QueryValueEx(key, "ProgId")
        return progid == _progid_for_extension(ext)
    except OSError:
        return False


def _is_default_linux(ext: str) -> bool:
    if not shutil.which("xdg-mime"):
        return False
    mime, _ = mimetypes.guess_type(f"file{ext}")
    if not mime:
        return False
    try:
        result = subprocess.run(["xdg-mime", "query", "default", mime], capture_output=True, text=True)
    except OSError:
        return False
    return result.stdout.strip() == "fosseverything.desktop"


def _register_app_capabilities_windows() -> tuple[bool, str]:
    """Register FOSSEverything as a candidate app for its supported file types (HKCU only, no elevation)."""
    try:
        import winreg  # noqa: 22
    except ImportError:
        return False, "winreg module not available."

    command_str = _resolve_windows_command()
    all_extensions = sorted({ext for _, extensions in FILE_FAMILIES for ext in extensions})

    try:
        cap_key = r"Software\FOSSEverything\Capabilities"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cap_key) as key:
            winreg.SetValueEx(key, "ApplicationName", 0, winreg.REG_SZ, APP_NAME)
            winreg.SetValueEx(key, "ApplicationDescription", 0, winreg.REG_SZ, APP_DESCRIPTION)

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cap_key + r"\FileAssociations") as key:
            for ext in all_extensions:
                winreg.SetValueEx(key, ext, 0, winreg.REG_SZ, _progid_for_extension(ext))

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\RegisteredApplications") as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cap_key)

        icon_path = app_icon_path()
        for ext in all_extensions:
            progid = _progid_for_extension(ext)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{progid}") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f"{APP_NAME} File")
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{progid}\DefaultIcon") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, icon_path)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{progid}\shell\open\command") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command_str)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{ext}\OpenWithProgids") as key:
                winreg.SetValueEx(key, progid, 0, winreg.REG_NONE, b"")

        return True, "Registered FOSSEverything as an available app for its supported file types."
    except Exception as exc:
        return False, f"Failed to register file associations: {exc}"


def _sh_open_with_dialog_windows(ext: str) -> bool:
    """Open the native Windows 'Open with' picker scoped to one extension (Vista+ SHOpenWithDialog)."""
    class _OpenAsInfo(ctypes.Structure):
        _fields_ = [
            ("pcszFile", ctypes.c_wchar_p),
            ("pcszClass", ctypes.c_wchar_p),
            ("oaifInFlags", ctypes.c_uint),
        ]

    # Only OAIF_REGISTER_EXT: no OAIF_EXEC (would launch on this nonexistent
    # dummy filename) and no OAIF_HIDE_REGISTRATION (hides "Always use this app").
    oaif_register_ext = 0x00000010

    info = _OpenAsInfo(f"choose{ext}", None, oaif_register_ext)
    result = ctypes.windll.shell32.SHOpenWithDialog(None, ctypes.byref(info))
    return result == 0


def set_default_for_extensions(extensions: Iterable[str]) -> tuple[bool, str]:
    """Best-effort per-platform default-app registration; falls back to manual instructions."""
    if sys.platform == "win32":
        return _set_default_windows(extensions)
    if sys.platform.startswith("linux"):
        return _set_default_linux(extensions)
    if sys.platform == "darwin":
        return _set_default_macos(extensions)
    return False, "Automatic default-app registration is not supported on this platform.\n\n" + manual_association_instructions(extensions)


# For these extensions the native picker just tells the user to use Settings instead.
_WINDOWS_HARDENED_EXTENSIONS = frozenset({".htm", ".html", ".jpg", ".jpeg", ".mp3", ".mp4", ".pdf", ".png", ".svg", ".wav"})


def _set_default_windows(extensions: Iterable[str]) -> tuple[bool, str]:
    """Register as a candidate app, then prompt the OS's native chooser for each extension.

    Windows has required explicit, per-extension user confirmation for default-app changes since
    Windows 8 (the UserChoice registry hash can't be set silently), so this can only open the native
    picker for the user to confirm, not force the association outright. A subset of extensions are
    further "hardened" (see _WINDOWS_HARDENED_EXTENSIONS) and can only be set via the Settings app.
    """
    ok, message = _register_app_capabilities_windows()
    if not ok:
        return False, message + "\n\n" + manual_association_instructions(extensions)

    extensions = sorted(extensions)
    hardened = [ext for ext in extensions if ext in _WINDOWS_HARDENED_EXTENSIONS]
    normal = [ext for ext in extensions if ext not in _WINDOWS_HARDENED_EXTENSIONS]

    prompted = [ext for ext in normal if _sh_open_with_dialog_windows(ext)]

    parts = []
    if prompted:
        parts.append(
            f"Opened the 'Open with' picker for: {', '.join(prompted)}.\n"
            "Select FOSSEverything and check \"Always use this app\" in each dialog."
        )
    if hardened:
        os.startfile("ms-settings:defaultapps")
        parts.append(
            f"Windows blocks apps from setting themselves as default for: {', '.join(hardened)}.\n"
            "Opened Settings > Apps > Default apps for you - search \"FOSSEverything\" there "
            "and select it for each of those file types."
        )

    if not parts:
        return False, "Could not open the system file-type picker.\n\n" + manual_association_instructions(extensions)
    return True, "\n\n".join(parts)


def _set_default_linux(extensions: Iterable[str]) -> tuple[bool, str]:
    """Set the default handler via xdg-mime, which applies immediately with no OS confirmation dialog."""
    if not shutil.which("xdg-mime"):
        return False, "The xdg-mime tool is not installed.\n\n" + manual_association_instructions(extensions)

    ok, message = _register_linux()
    if not ok:
        return False, message + "\n\n" + manual_association_instructions(extensions)

    updated = []
    for ext in sorted(extensions):
        mime, _ = mimetypes.guess_type(f"file{ext}")
        if not mime:
            continue
        result = subprocess.run(["xdg-mime", "default", "fosseverything.desktop", mime], capture_output=True)
        if result.returncode == 0:
            updated.append(ext)

    if not updated:
        return False, "Could not determine a MIME type for the selected file types.\n\n" + manual_association_instructions(extensions)
    return True, f"Set FOSSEverything as the default app for: {', '.join(updated)}."


def _set_default_macos(extensions: Iterable[str]) -> tuple[bool, str]:
    """macOS only lets a properly bundled .app register default handlers via LaunchServices."""
    return False, (
        "Automatic default-app registration on macOS requires FOSSEverything to be built as a "
        "signed .app bundle with declared document types; it isn't when run from source.\n\n"
    ) + manual_association_instructions(extensions)


# ─── Linux ───────────────────────────────────────────────────────────────────
def _register_linux(exe_path: str | None = None) -> tuple[bool, str]:
    """Install XDG Desktop entry and KDE/GNOME context menu action."""
    if not exe_path:
        if getattr(sys, "frozen", False):
            exe_path = sys.executable
        else:
            exe_path = f'{sys.executable} {os.path.abspath(sys.argv[0])}'

    desktop_content = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
GenericName=Local Desktop Power Tool
Comment={APP_DESCRIPTION}
Exec={exe_path} %F
Icon=utilities-terminal
Terminal=false
Categories=Utility;Graphics;AudioVideo;Office;
MimeType=application/pdf;image/png;image/jpeg;image/webp;image/gif;video/mp4;video/quicktime;video/x-matroska;audio/mpeg;audio/wav;audio/flac;application/json;application/yaml;text/csv;
"""
    try:
        app_dir = os.path.expanduser("~/.local/share/applications")
        os.makedirs(app_dir, exist_ok=True)
        desktop_file = os.path.join(app_dir, "fosseverything.desktop")
        with open(desktop_file, "w", encoding="utf-8") as f:
            f.write(desktop_content)

        if shutil.which("update-desktop-database"):
            subprocess.run(["update-desktop-database", app_dir], capture_output=True)

        return True, f"Successfully created FreeDesktop entry at:\n  {desktop_file}"
    except Exception as exc:
        return False, f"Failed to create Linux desktop entry: {exc}"


def _unregister_linux() -> tuple[bool, str]:
    try:
        desktop_file = os.path.expanduser("~/.local/share/applications/fosseverything.desktop")
        if os.path.exists(desktop_file):
            os.remove(desktop_file)
        return True, "Removed FOSSEverything Linux desktop integration."
    except Exception as exc:
        return False, f"Failed to remove desktop entry: {exc}"


# ─── macOS ───────────────────────────────────────────────────────────────────
def _register_macos(exe_path: str | None = None) -> tuple[bool, str]:
    """Create local user launcher in ~/.local/bin/fosseverything."""
    if not exe_path:
        if getattr(sys, "frozen", False):
            exe_path = sys.executable
        else:
            exe_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'

    bin_dir = os.path.expanduser("~/.local/bin")
    os.makedirs(bin_dir, exist_ok=True)
    launcher = os.path.join(bin_dir, "fosseverything")
    try:
        with open(launcher, "w", encoding="utf-8") as f:
            f.write(f"#!/usr/bin/env bash\nexec {exe_path} \"$@\"\n")
        os.chmod(launcher, 0o755)
        return True, f"Successfully installed CLI launcher at:\n  {launcher}\n(Ensure ~/.local/bin is in your PATH)"
    except Exception as exc:
        return False, f"Failed to create macOS launcher: {exc}"


def _unregister_macos() -> tuple[bool, str]:
    launcher = os.path.expanduser("~/.local/bin/fosseverything")
    if os.path.exists(launcher):
        try:
            os.remove(launcher)
            return True, "Removed macOS launcher."
        except Exception as exc:
            return False, str(exc)
    return True, "No launcher found."
