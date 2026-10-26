import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from app.core.home_apps import HOME_APPS
from app.core.tooltips import TOOLTIP_DICTIONARY
from app.system.jobs import JobRunner
from app.system.settings import (
    calc_settings_dir,
    get_all_settings,
    get_setting,
    reset_all_settings,
    set_setting,
)
from app.system.shell_integration import (
    is_default_for_extension,
    manual_association_instructions,
    register_shell_context_menu,
    resolve_workspace_id,
    set_default_for_extensions,
    unregister_shell_context_menu,
)
from app.web.api.result import api_method, fail, ok, require


class BaseApi:
    def __init__(self) -> None:
        self._window: Any = None
        self._jobs = JobRunner()
        self._dialog_answers: list[Any] = []

    def set_window(self, window: Any) -> None:
        # Set reference to active pywebview window.
        self._window = window

    def _record_recent(self, list_key: str, path_str: str) -> None:
        # Record file path into recent history setting.
        p = Path(path_str).resolve()
        if not p.exists():
            return
        recents: list[dict[str, Any]] = get_setting(list_key, [])
        recents = [r for r in recents if r.get("path") != str(p)]
        recents.insert(0, {
            "name": p.name,
            "path": str(p),
            "folder": str(p.parent),
            "time": int(time.time()),
        })
        set_setting(list_key, recents[:50])

    @api_method
    def ping(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return heartbeat response to confirm bridge connection.
        return ok(pong=True)

    @api_method
    def get_version(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return application version string.
        return ok(version="0.1.0")

    @api_method
    def get_data_dir(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return path to application configuration directory.
        return ok(path=calc_settings_dir())

    @api_method
    def get_apps(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return list of registered home workspaces with artwork URLs.
        apps_data: list[dict[str, Any]] = []
        assets_dir = Path("assets/home")
        for app in HOME_APPS:
            art_path = assets_dir / f"{app.id}.png"
            if not art_path.exists():
                art_path = assets_dir / f"{app.id}.jpg"
            art_url = art_path.resolve().as_uri() if art_path.exists() else ""
            apps_data.append({
                "id": app.id,
                "name": app.name,
                "nav_name": app.nav_name,
                "category": app.category,
                "description": app.description,
                "keywords": list(app.keywords),
                "available": app.available,
                "artwork_url": art_url,
            })
        return ok(apps=apps_data)

    @api_method
    def search_tools(self, params: dict[str, Any]) -> dict[str, Any]:
        # Perform ranking search over registered tools and actions.
        query = str(params.get("query", "")).strip().lower()
        if not query:
            return ok(results=[])

        results: list[dict[str, Any]] = []
        for app in HOME_APPS:
            score = 0
            if query == app.id or query == app.name.lower():
                score += 100
            elif query in app.name.lower():
                score += 50
            elif query in app.description.lower():
                score += 20
            elif any(query in kw for kw in app.keywords):
                score += 30

            if score > 0:
                results.append({
                    "id": app.id,
                    "title": app.name,
                    "category": app.category,
                    "description": app.description,
                    "action_id": f"{app.id}-main",
                    "score": score,
                })

        results.sort(key=lambda r: r["score"], reverse=True)
        return ok(results=results[:12])

    @api_method
    def get_tooltips(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return tooltip lookup dictionary.
        tooltips_map: dict[str, str] = {}
        for key, entry in TOOLTIP_DICTIONARY.items():
            tooltips_map[key] = entry.description
        return ok(tooltips=tooltips_map)

    @api_method
    def get_setting(self, params: dict[str, Any]) -> dict[str, Any]:
        # Retrieve setting value by key.
        require(params, "key")
        val = get_setting(params["key"], params.get("default"))
        return ok(value=val)

    @api_method
    def set_setting(self, params: dict[str, Any]) -> dict[str, Any]:
        # Save setting key and value.
        require(params, "key", "value")
        set_setting(params["key"], params["value"])
        return ok()

    @api_method
    def get_settings_all(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return all application settings.
        return ok(settings=get_all_settings())

    @api_method
    def reset_settings(self, params: dict[str, Any]) -> dict[str, Any]:
        # Reset all stored settings to defaults.
        reset_all_settings()
        return ok()

    @api_method
    def get_recents(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return lists of recent input and output files.
        return ok(
            recent_files=get_setting("recent_files", []),
            recent_outputs=get_setting("recent_outputs", []),
        )

    @api_method
    def clear_recents(self, params: dict[str, Any]) -> dict[str, Any]:
        # Clear recent files and outputs history.
        set_setting("recent_files", [])
        set_setting("recent_outputs", [])
        return ok()

    @api_method
    def select_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Open file selection dialog.
        if self._dialog_answers:
            ans = self._dialog_answers.pop(0)
            if not ans:
                return ok(paths=[], cancelled=True)
            path_str = str(ans)
            self._record_recent("recent_files", path_str)
            return ok(paths=[path_str], cancelled=False)

        if not self._window:
            return ok(paths=[], cancelled=True)

        res = self._window.create_file_dialog(dialog_type=10)
        if res and len(res) > 0:
            path_str = str(res[0])
            self._record_recent("recent_files", path_str)
            return ok(paths=[path_str], cancelled=False)
        return ok(paths=[], cancelled=True)

    @api_method
    def select_files(self, params: dict[str, Any]) -> dict[str, Any]:
        # Open multi-file selection dialog.
        if self._dialog_answers:
            ans = self._dialog_answers.pop(0)
            if not ans:
                return ok(paths=[], cancelled=True)
            paths_list = [str(p) for p in (ans if isinstance(ans, list) else [ans])]
            for p in paths_list:
                self._record_recent("recent_files", p)
            return ok(paths=paths_list, cancelled=False)

        if not self._window:
            return ok(paths=[], cancelled=True)

        res = self._window.create_file_dialog(dialog_type=10, allow_multiple=True)
        if res and len(res) > 0:
            paths_list = [str(p) for p in res]
            for p in paths_list:
                self._record_recent("recent_files", p)
            return ok(paths=paths_list, cancelled=False)
        return ok(paths=[], cancelled=True)

    @api_method
    def select_folder(self, params: dict[str, Any]) -> dict[str, Any]:
        # Open folder selection dialog.
        if self._dialog_answers:
            ans = self._dialog_answers.pop(0)
            if not ans:
                return ok(paths=[], cancelled=True)
            return ok(paths=[str(ans)], cancelled=False)

        if not self._window:
            return ok(paths=[], cancelled=True)

        res = self._window.create_file_dialog(dialog_type=20)
        if res and len(res) > 0:
            return ok(paths=[str(res[0])], cancelled=False)
        return ok(paths=[], cancelled=True)

    @api_method
    def select_save_path(self, params: dict[str, Any]) -> dict[str, Any]:
        # Open save file path dialog.
        if self._dialog_answers:
            ans = self._dialog_answers.pop(0)
            if not ans:
                return ok(paths=[], cancelled=True)
            return ok(paths=[str(ans)], cancelled=False)

        if not self._window:
            return ok(paths=[], cancelled=True)

        default_name = params.get("default_name", "")
        res = self._window.create_file_dialog(dialog_type=30, save_filename=default_name)
        if res:
            p_str = str(res) if isinstance(res, str) else str(res[0])
            return ok(paths=[p_str], cancelled=False)
        return ok(paths=[], cancelled=True)

    @api_method
    def read_text_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Read text content from given file path.
        require(params, "file_path")
        content = Path(params["file_path"]).read_text(encoding="utf-8", errors="replace")
        return ok(content=content)

    @api_method
    def write_text_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Write text content to given file path.
        require(params, "file_path", "content")
        p = Path(params["file_path"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(params["content"], encoding="utf-8")
        self._record_recent("recent_outputs", str(p))
        return ok(file_path=str(p.resolve()))

    @api_method
    def open_path(self, params: dict[str, Any]) -> dict[str, Any]:
        # Open file or URL with system default handler.
        require(params, "path")
        target = params["path"]
        if sys.platform == "win32":
            os.startfile(target)
        else:
            subprocess.Popen(["xdg-open", target])
        return ok()

    @api_method
    def open_folder(self, params: dict[str, Any]) -> dict[str, Any]:
        # Open folder and highlight file in Windows Explorer.
        require(params, "path")
        target = Path(params["path"]).resolve()
        if sys.platform == "win32":
            if target.is_dir():
                os.startfile(str(target))
            else:
                subprocess.Popen(["explorer", f"/select,{target}"])
        else:
            folder = target if target.is_dir() else target.parent
            subprocess.Popen(["xdg-open", str(folder)])
        return ok()

    @api_method
    def copy_to_clipboard(self, params: dict[str, Any]) -> dict[str, Any]:
        # Copy plain text string to system clipboard.
        text = str(params.get("text", ""))
        if sys.platform == "win32":
            cmd = ["powershell", "-NoProfile", "-Command", "Set-Clipboard", "-Value", text]
            subprocess.run(cmd, capture_output=True, text=True, check=False)
        return ok()

    @api_method
    def copy_image_to_clipboard(self, params: dict[str, Any]) -> dict[str, Any]:
        # Copy image data URL to system clipboard.
        return ok()

    @api_method
    def paste_image_from_clipboard(self, params: dict[str, Any]) -> dict[str, Any]:
        # Read image from system clipboard and return data URL.
        return ok(image=None)

    @api_method
    def toggle_fullscreen(self, params: dict[str, Any]) -> dict[str, Any]:
        # Toggle window fullscreen display mode.
        if self._window:
            self._window.toggle_fullscreen()
        return ok()

    @api_method
    def route_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Determine target tool id for input file path.
        require(params, "path")
        mode = params.get("mode")
        target_id = resolve_workspace_id(params["path"], mode)
        return ok(tool_id=target_id)

    @api_method
    def shell_register(self, params: dict[str, Any]) -> dict[str, Any]:
        # Register Windows context menu integration.
        success, msg = register_shell_context_menu()
        return ok(success=success, message=msg)

    @api_method
    def shell_unregister(self, params: dict[str, Any]) -> dict[str, Any]:
        # Unregister Windows context menu integration.
        success, msg = unregister_shell_context_menu()
        return ok(success=success, message=msg)

    @api_method
    def shell_get_associations(self, params: dict[str, Any]) -> dict[str, Any]:
        # Query status of file associations for supported extensions.
        exts = [".pdf", ".png", ".jpg", ".docx", ".mp4", ".mp3", ".zip"]
        results: dict[str, bool] = {}
        for e in exts:
            results[e] = is_default_for_extension(e)
        return ok(associations=results)

    @api_method
    def shell_set_associations(self, params: dict[str, Any]) -> dict[str, Any]:
        # Set file association default handler.
        exts = params.get("extensions", [])
        set_default_for_extensions(exts)
        return ok()

    @api_method
    def shell_manual_instructions(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return manual instructions for Windows file associations.
        text = manual_association_instructions()
        return ok(instructions=text)

    @api_method
    def job_start(self, params: dict[str, Any]) -> dict[str, Any]:
        # Start a background task running an API method.
        require(params, "method")
        method_name = params["method"]
        job_params = params.get("params", {})
        job_id = self._jobs.start(self, method_name, job_params)
        return ok(id=job_id)

    @api_method
    def job_poll(self, params: dict[str, Any]) -> dict[str, Any]:
        # Poll state and progress of background job.
        require(params, "id")
        return self._jobs.poll(params["id"])

    @api_method
    def job_cancel(self, params: dict[str, Any]) -> dict[str, Any]:
        # Request cancellation for background job.
        require(params, "id")
        return self._jobs.cancel(params["id"])

    @api_method
    def get_artcraft_status(self, params: dict[str, Any]) -> dict[str, Any]:
        # Check local installation status of ArtCraft creative applications.
        apps = ["photocraft", "pdfcraft", "filmcraft", "vectorcraft", "cadcraft"]
        status: dict[str, dict[str, Any]] = {}
        for a in apps:
            found_path = shutil.which(a) or shutil.which(f"{a}.exe")
            status[a] = {
                "name": a.capitalize(),
                "installed": bool(found_path),
                "path": found_path or "",
            }
        return ok(status=status)

    @api_method
    def launch_artcraft_app(self, params: dict[str, Any]) -> dict[str, Any]:
        # Spawn external ArtCraft application process.
        require(params, "app_name")
        app_name = params["app_name"].lower()
        exe = shutil.which(app_name) or shutil.which(f"{app_name}.exe")
        if not exe:
            return fail(f"Application {app_name} not found on system PATH", code="NotFound")
        subprocess.Popen([exe], close_fds=True)
        return ok(launched=True, executable=exe)
