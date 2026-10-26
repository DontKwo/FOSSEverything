from typing import Any

from app.features.renamer.ops import (
    RenamePlan,
    execute_renames,
    find_new_files_for_plan,
    plan_consolidate_to_folder,
    preview_renames,
    save_cross_folder_plan,
    save_preset,
    sort_files_by_timeline,
    undo_renames,
)
from app.web.api.result import api_method, ok, require


class RenamerApiMixin:
    @api_method
    def renamer_preview(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate rename plan preview with collisions and proposed paths.
        require(params, "file_paths")
        paths = list(params["file_paths"])
        mode = str(params.get("mode", "template"))
        plan_params = dict(params.get("options", params))
        plans = preview_renames(paths, mode, plan_params)
        has_conflicts = any(p.has_collision for p in plans)
        return ok(
            entries=[{
                "original": p.old_path,
                "proposed": p.new_path,
                "old_name": p.old_name,
                "new_name": p.new_name,
                "error": p.error,
                "has_collision": p.has_collision,
            } for p in plans],
            has_conflicts=has_conflicts,
        )

    @api_method
    def renamer_execute(self, params: dict[str, Any]) -> dict[str, Any]:
        # Execute batch file renames based on plan.
        require(params, "file_paths")
        paths = list(params["file_paths"])
        mode = str(params.get("mode", "template"))
        plan_params = dict(params.get("options", params))
        plans = preview_renames(paths, mode, plan_params)
        results = execute_renames(plans)
        return ok(
            results=[{
                "original": r.old_path,
                "target": r.new_path,
                "success": r.success,
                "error": r.error,
            } for r in results]
        )

    @api_method
    def renamer_apply(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for executing batch renames.
        return self.renamer_execute(params)

    @api_method
    def renamer_undo(self, params: dict[str, Any]) -> dict[str, Any]:
        # Revert previously executed rename operations.
        require(params, "results")
        undo_items: list[tuple[str, str]] = []
        for r in params["results"]:
            if isinstance(r, dict) and r.get("success"):
                undo_items.append((r["target"], r["original"]))
        res = undo_renames(undo_items)
        return ok(undone=res)

    @api_method
    def renamer_find_new_files(self, params: dict[str, Any]) -> dict[str, Any]:
        # Identify recently added files eligible for renaming plan.
        require(params, "directory_path")
        dir_p = str(params["directory_path"])
        exts = params.get("extensions")
        files = find_new_files_for_plan(dir_p, extensions=exts)
        return ok(files=files)

    @api_method
    def renamer_consolidate(self, params: dict[str, Any]) -> dict[str, Any]:
        # Plan consolidation of files across subdirectories into target folder.
        require(params, "source_paths", "target_dir")
        sources = list(params["source_paths"])
        target_dir = str(params["target_dir"])
        plan = plan_consolidate_to_folder(sources, target_dir)
        return ok(plan=[{"src": str(p[0]), "dst": str(p[1])} for p in plan])

    @api_method
    def renamer_sort_timeline(self, params: dict[str, Any]) -> dict[str, Any]:
        # Sort files by camera EXIF creation date or file timestamps.
        require(params, "file_paths")
        paths = list(params["file_paths"])
        sorted_paths = sort_files_by_timeline(paths)
        return ok(sorted_paths=sorted_paths)

    @api_method
    def renamer_save_plan(self, params: dict[str, Any]) -> dict[str, Any]:
        # Save cross-folder rename plan to JSON file.
        require(params, "plan", "output_path")
        plan_dict = dict(params["plan"])
        out_p = str(params["output_path"])
        save_cross_folder_plan(plan_dict, out_p)
        return ok(output_path=out_p)

    @api_method
    def renamer_save_preset(self, params: dict[str, Any]) -> dict[str, Any]:
        # Save rename pattern template to presets file.
        require(params, "preset_name", "template")
        save_preset(str(params["preset_name"]), str(params["template"]))
        return ok(saved=True)
