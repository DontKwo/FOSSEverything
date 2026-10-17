"""Entry point for FOSSEverything - Local Desktop Power Tool.

Run with:  python main.py [optional_file_path]
"""
import sys
import os
import signal
import ctypes

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from app.system import shell_integration

# Suppress Qt internal multimedia/FFmpeg verbose startup messages before any Qt import
os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.ffmpeg=false;qt.multimedia=false;qt.multimedia.ffmpeg.info=false;qt.multimedia.ffmpeg.warning=false")


def main() -> None:
    if "--register-shell" in sys.argv:
        ok, msg = shell_integration.register_shell_context_menu()
        print(msg)  # noqa: 25 (CLI status output, not debug)
        sys.exit(0 if ok else 1)

    if "--unregister-shell" in sys.argv:
        ok, msg = shell_integration.unregister_shell_context_menu()
        print(msg)  # noqa: 25 (CLI status output, not debug)
        sys.exit(0 if ok else 1)

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    target_file = os.path.abspath(args[0]) if args else None
    force_mode = None
    if "--ocr" in sys.argv:
        force_mode = "ocr"
    elif "--hash" in sys.argv:
        force_mode = "hash"

    if sys.platform == "win32":
        # Without a distinct App User Model ID, Windows groups this process under
        # its host interpreter (python.exe) in the taskbar instead of as its own app.
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FOSSEverything.DesktopApp")

    # Warm the routed file's tab module in the background now, overlapping its
    # heavy imports (e.g. numpy/pymupdf) with everything else below.
    if target_file:
        shell_integration.preload_workspace_module_in_background(target_file, force_mode)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("FOSSEverything")
    icon_path = shell_integration.app_icon_path()
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Let Ctrl+C quit the app. Qt's event loop never yields to the Python
    # interpreter on its own, so a periodic no-op timer is needed to let it notice the signal.
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    sigint_timer = QTimer()
    sigint_timer.timeout.connect(lambda: None)
    sigint_timer.start(200)

    # If an instance is already running, hand it the file and exit instead of
    # paying the full cold-start cost (importing and building every tab) again.
    if shell_integration.try_forward_to_running_instance(target_file, force_mode):
        sys.exit(0)

    from app.ui.main_window import MainWindow
    window = MainWindow()
    window._ipc_server = shell_integration.start_ipc_server(window)  # noqa: 21 (kept alive for the window's lifetime, never read)

    if not window.settings.value("app/setup_wizard_complete", False, type=bool):
        from app.ui.setup_wizard import SetupWizard
        SetupWizard(window.settings, main_window=window).exec()
        window.settings.setValue("app/setup_wizard_complete", True)

    # Show the window frame first; deferring the workspace/file load keeps a
    # slow tab build (e.g. opening a PDF) from blocking the first paint.
    window.show()
    if target_file:
        QTimer.singleShot(0, lambda: shell_integration.route_file(window, target_file, force_mode=force_mode))
    else:
        QTimer.singleShot(0, window.go_home)

    # Model3D Studio's pyvista/vtk import is the heaviest per-tab dependency (1-3s
    # cold); pre-warm it in the background now so it's ready by the time it's opened.
    from app.features.model3d.viewport import preload_vtk_stack_in_background
    preload_vtk_stack_in_background()

    # Deferred (not called inline) so these registry writes never delay the first
    # paint of the window/routed file -- they run once the event loop is already idle.
    QTimer.singleShot(0, shell_integration.ensure_open_with_candidacy)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
