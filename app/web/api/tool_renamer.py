import os
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
        if params.get("timeline"):
            paths = sort_files_by_timeline(paths)
        mode = str(params.get("mode", "template"))
        plan_params = dict(params.get("options", params))
        plans = preview_renames(paths, mode, plan_params)
        consolidate_dir = str(params.get("consolidate_to", "")).strip()
        if consolidate_dir:
            plans = plan_consolidate_to_folder(plans, consolidate_dir)
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
        if params.get("timeline"):
            paths = sort_files_by_timeline(paths)
        mode = str(params.get("mode", "template"))
        plan_params = dict(params.get("options", params))
        plans = preview_renames(paths, mode, plan_params)
        consolidate_dir = str(params.get("consolidate_to", "")).strip()
        if consolidate_dir:
            plans = plan_consolidate_to_folder(plans, consolidate_dir)
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
        # Revert previously executed rename operations safely.
        require(params, "results")
        undo_items: list[tuple[str, str]] = []
        for r in params["results"]:
            if isinstance(r, dict) and r.get("success"):
                orig = r.get("original")
                target = r.get("target")
                if orig and target and orig != target:
                    undo_items.append((target, orig))
        pairs = undo_renames(undo_items)
        plans = [
            RenamePlan(
                old_path=curr,
                old_name=os.path.basename(curr),
                new_name=os.path.basename(orig),
                new_path=orig,
            )
            for curr, orig in pairs
        ]
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
    def renamer_find_new_files(self, params: dict[str, Any]) -> dict[str, Any]:
        # Identify recently added files eligible for renaming plan.
        source_folders = list(params.get("source_folders", []))
        if not source_folders and "directory_path" in params:
            source_folders = [str(params["directory_path"])]
        processed = list(params.get("processed_files", []))
        files = find_new_files_for_plan(source_folders, processed)
        return ok(files=files)

    @api_method
    def renamer_consolidate(self, params: dict[str, Any]) -> dict[str, Any]:
        # Plan consolidation of files across subdirectories into target folder.
        require(params, "file_paths", "target_dir")
        paths = list(params["file_paths"])
        target_dir = str(params["target_dir"])
        mode = str(params.get("mode", "template"))
        plan_params = dict(params.get("options", params))
        plans = preview_renames(paths, mode, plan_params)
        consolidated = plan_consolidate_to_folder(plans, target_dir)
        return ok(entries=[{
            "original": p.old_path,
            "proposed": p.new_path,
            "old_name": p.old_name,
            "new_name": p.new_name,
            "error": p.error,
            "has_collision": p.has_collision,
        } for p in consolidated])

    @api_method
    def renamer_sort_timeline(self, params: dict[str, Any]) -> dict[str, Any]:
        # Sort files by camera EXIF creation date or file timestamps.
        require(params, "file_paths")
        paths = list(params["file_paths"])
        sorted_paths = sort_files_by_timeline(paths)
        return ok(sorted_paths=sorted_paths)

    @api_method
    def renamer_save_plan(self, params: dict[str, Any]) -> dict[str, Any]:
        # Save cross-folder rename plan configuration.
        require(params, "name", "source_folders")
        name = str(params["name"])
        source_folders = list(params["source_folders"])
        mode = str(params.get("mode", "template"))
        plan_params = dict(params.get("options", params.get("params", {})))
        target_dir = params.get("target_dir")
        processed_files = list(params.get("processed_files", []))
        plan_data = save_cross_folder_plan(
            name=name,
            source_folders=source_folders,
            mode=mode,
            params=plan_params,
            target_dir=str(target_dir) if target_dir else None,
            processed_files=processed_files,
        )
        return ok(plan=plan_data)

    @api_method
    def renamer_save_preset(self, params: dict[str, Any]) -> dict[str, Any]:
        # Save rename pattern template to presets dict.
        require(params, "preset_name")
        preset_name = str(params["preset_name"])
        mode = str(params.get("mode", "template"))
        preset_params = dict(params.get("options", params.get("params", {})))
        if "template" in params and "template" not in preset_params:
            preset_params["template"] = params["template"]
        preset_data = save_preset(preset_name, mode, preset_params)
        return ok(saved=True, preset=preset_data)
