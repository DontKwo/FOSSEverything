import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from app.core.home_apps import HOME_APPS
from app.core.tooltips import TOOLTIP_DICTIONARY
from app.system.jobs import JobRunner
from app.system.settings import (
    calc_app_base_dir,
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


def format_dialog_file_types(types_param: Any) -> tuple[str, ...]:
    # Format file extensions for pywebview create_file_dialog.
    if not types_param:
        return ('All Files (*.*)',)
    if isinstance(types_param, str):
        types_param = [t.strip() for t in types_param.split(',') if t.strip()]
    if isinstance(types_param, (list, tuple, set)):
        clean_exts = [str(ext).lstrip('.*').lower() for ext in types_param if str(ext).strip()]
        if clean_exts:
            patterns = ';'.join(f'*.{e}' for e in clean_exts)
            return (f'Supported Files ({patterns})', 'All Files (*.*)')
    return ('All Files (*.*)',)


_EXT_PATTERN = re.compile(r"\.([A-Za-z0-9]{1,5})$")


def _split_extension(name: str) -> tuple[str, str]:
    # Split a default file name into base name and lowercase extension.
    match = _EXT_PATTERN.search(name)
    if not match:
        return name, ""
    return name[: match.start()], match.group(1).lower()


def _build_save_types(file_types: Any, name_ext: str) -> tuple[tuple[str, ...], list[str]]:
    # Build pywebview filter strings and the flat list of allowed extensions.
    dialog_types: list[str] = []
    allowed: list[str] = []
    entries: list[Any] = list(file_types) if isinstance(file_types, (list, tuple)) else []
    if not entries and name_ext:
        entries = [{"name": f"{name_ext.upper()} File", "extensions": [name_ext]}]
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        exts = [str(e).lstrip(".*").lower() for e in entry.get("extensions", []) if str(e).strip()]
        if not exts:
            continue
        patterns = ";".join(f"*.{e}" for e in exts)
        label = str(entry.get("name", "Files"))
        dialog_types.append(label if "(*." in label else f"{label} ({patterns})")
        allowed.extend(e for e in exts if e not in allowed)
    return tuple(dialog_types), allowed


def _apply_save_extension(path_str: str, allowed_exts: list[str]) -> str:
    # Append the first allowed extension when the chosen path lacks a matching one.
    if not allowed_exts:
        return path_str
    lowered = path_str.lower()
    if any(lowered.endswith(f".{ext}") for ext in allowed_exts):
        return path_str
    return f"{path_str}.{allowed_exts[0]}"


class BaseApi:
    def __init__(self) -> None:
        self._window: Any = None
        self._jobs = JobRunner()
        self._dialog_answers: list[Any] = []

    def _set_window(self, window: Any) -> None:
        # Set reference to active pywebview window.
        self._window = window

    def _record_recent(self, list_key: str, path_str: str) -> None:
        # Record file path into recent history setting.
        p = Path(path_str).resolve()
        if not p.exists():
            return
        recents: list[dict[str, Any]] = get_setting(list_key, [])
        recents = [item for item in recents if item.get("path") != str(p)]
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
        base_dir = calc_app_base_dir()
        web_assets = base_dir / "app" / "web" / "assets" / "home"
        root_assets = base_dir / "assets" / "home"
        for app in HOME_APPS:
            art_url = ""
            for ext in ("png", "jpg", "svg"):
                if (web_assets / f"{app.id}.{ext}").exists() or (root_assets / f"{app.id}.{ext}").exists():
                    art_url = f"assets/home/{app.id}.{ext}"
                    break
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

        results: list[dict[str, Any]] = []
        for app in HOME_APPS:
            score = 0
            if not query:
                score = 10
            elif query == app.id or query == app.name.lower():
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
        setting_val = get_setting(params["key"], params.get("default"))
        return ok(value=setting_val)

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
    def reset_settings_defaults(self, params: dict[str, Any]) -> dict[str, Any]:
        # Reset user preferences in settings while preserving defaults.
        reset_all_settings()
        set_setting("theme", "dark")
        set_setting("ui_scale", 1.0)
        return ok(message="Settings reset to defaults")

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

        ft = format_dialog_file_types(params.get('file_types'))
        res = self._window.create_file_dialog(dialog_type=10, file_types=ft)
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
                return ok(paths=[], file_paths=[], cancelled=True)
            paths_list = [str(p) for p in (ans if isinstance(ans, list) else [ans])]
            for p in paths_list:
                self._record_recent("recent_files", p)
            return ok(paths=paths_list, file_paths=paths_list, cancelled=False)

        if not self._window:
            return ok(paths=[], file_paths=[], cancelled=True)

        ft = format_dialog_file_types(params.get('file_types'))
        res = self._window.create_file_dialog(dialog_type=10, allow_multiple=True, file_types=ft)
        if res and len(res) > 0:
            paths_list = [str(p) for p in res]
            for p in paths_list:
                self._record_recent("recent_files", p)
            return ok(paths=paths_list, file_paths=paths_list, cancelled=False)
        return ok(paths=[], file_paths=[], cancelled=True)

    @api_method
    def select_folder(self, params: dict[str, Any]) -> dict[str, Any]:
        # Open folder selection dialog.
        if self._dialog_answers:
            ans = self._dialog_answers.pop(0)
            if not ans:
                return ok(paths=[], path="", folder_path="", output_dir="", cancelled=True)
            p_str = str(ans)
            return ok(paths=[p_str], path=p_str, folder_path=p_str, output_dir=p_str, cancelled=False)

        if not self._window:
            return ok(paths=[], path="", folder_path="", output_dir="", cancelled=True)

        res = self._window.create_file_dialog(dialog_type=20)
        if res and len(res) > 0:
            p_str = str(res[0])
            return ok(paths=[p_str], path=p_str, folder_path=p_str, output_dir=p_str, cancelled=False)
        return ok(paths=[], path="", folder_path="", output_dir="", cancelled=True)

    @api_method
    def select_save_path(self, params: dict[str, Any]) -> dict[str, Any]:
        # Open save dialog with a clean base name and a Save as type dropdown.
        default_name = str(params.get("default_name", "")).strip()
        base_name, name_ext = _split_extension(default_name)
        dialog_types, allowed_exts = _build_save_types(params.get("file_types"), name_ext)

        if self._dialog_answers:
            ans = self._dialog_answers.pop(0)
            if not ans:
                return ok(paths=[], path="", file_path="", output_path="", cancelled=True)
            p_str = _apply_save_extension(str(ans), allowed_exts)
            return ok(paths=[p_str], path=p_str, file_path=p_str, output_path=p_str, cancelled=False)

        if not self._window:
            return ok(paths=[], path="", file_path="", output_path="", cancelled=True)

        res = self._window.create_file_dialog(
            dialog_type=30, save_filename=base_name, file_types=dialog_types
        )
        if res:
            p_str = _apply_save_extension(str(res) if isinstance(res, str) else str(res[0]), allowed_exts)
            return ok(paths=[p_str], path=p_str, file_path=p_str, output_path=p_str, cancelled=False)
        return ok(paths=[], path="", file_path="", output_path="", cancelled=True)

    @api_method
    def get_theme_palette(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return theme color palette dictionary.
        theme_name = str(params.get("theme_name", "dark"))
        from app.core.theme import default_palette
        palette = default_palette(theme_name)
        return ok(**palette, palette=palette)

    @api_method
    def read_text_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Read text content from given file path.
        fp = params.get("file_path") or params.get("path")
        if not fp:
            return fail("Parameter 'file_path' or 'path' is required", code="MissingParameter")
        content = Path(fp).read_text(encoding="utf-8", errors="replace")
        return ok(content=content, text=content)

    @api_method
    def read_file_text(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for reading text file.
        return self.read_text_file(params)

    @api_method
    def write_text_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Write text content to given file path.
        target_path_str = params.get("file_path") or params.get("path")
        if not target_path_str:
            return fail("Missing required parameter: file_path or path")
        require(params, "content")
        target_path = Path(str(target_path_str))
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(params["content"], encoding="utf-8")
        self._record_recent("recent_outputs", str(target_path))
        resolved_path = str(target_path.resolve())
        return ok(file_path=resolved_path, path=resolved_path)

    @api_method
    def save_file(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for writing text content.
        return self.write_text_file(params)

    @api_method
    def save_file_text(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for saving text file.
        return self.write_text_file(params)

    @api_method
    def select_directory(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for selecting folder dialog.
        return self.select_folder(params)

    @api_method
    def save_file_dialog(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for selecting save path dialog.
        return self.select_save_path(params)

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
        # Query status of file associations for supported extensions with memoized cache.
        refresh = bool(params.get("refresh", False))
        cached = getattr(self, "_cached_associations", None)
        if cached is not None and not refresh:
            return ok(associations=cached)
        exts = [".pdf", ".png", ".jpg", ".docx", ".mp4", ".mp3", ".zip"]
        results: dict[str, bool] = {}
        for e in exts:
            results[e] = is_default_for_extension(e)
        self._cached_associations = results
        return ok(associations=results)

    @api_method
    def shell_set_associations(self, params: dict[str, Any]) -> dict[str, Any]:
        # Set file association default handler and invalidate cached associations.
        exts = params.get("extensions", [])
        set_default_for_extensions(exts)
        self._cached_associations = None
        return ok()

    @api_method
    def shell_manual_instructions(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return manual instructions for Windows file associations.
        exts = params.get('extensions') or ['.pdf', '.png', '.docx', '.zip']
        text = manual_association_instructions(exts)
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
