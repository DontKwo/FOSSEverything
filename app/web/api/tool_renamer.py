import os
from typing import Any

from app.features.renamer.ops import (
    RenamePlan,
    STARTER_RECIPES,
    execute_renames,
    find_new_files_for_plan,
    plan_consolidate_to_folder,
    preview_renames,
    preview_step_pipeline,
    save_cross_folder_plan,
    save_preset,
    sort_files_by_timeline,
    undo_renames,
)
from app.system.settings import get_setting, set_setting
from app.web.api.result import api_method, ok, require


class RenamerApiMixin:
    @api_method
    def renamer_scan_inputs(self, params: dict[str, Any]) -> dict[str, Any]:
        # Scan files and directory paths recursively or shallowly for batch renaming.
        raw_paths = list(params.get("paths", []))
        recursive = bool(params.get("recursive", False))
        found_files: list[str] = []

        for p in raw_paths:
            path_str = str(p).strip()
            if not path_str:
                continue
            if os.path.isfile(path_str):
                if path_str not in found_files:
                    found_files.append(path_str)
            elif os.path.isdir(path_str):
                if recursive:
                    for root, _, files in os.walk(path_str):
                        for f in files:
                            full = os.path.join(root, f)
                            if full not in found_files:
                                found_files.append(full)
                else:
                    try:
                        for entry in os.listdir(path_str):
                            full = os.path.join(path_str, entry)
                            if os.path.isfile(full) and full not in found_files:
                                found_files.append(full)
                    except OSError:
                        continue

        return ok(paths=found_files, count=len(found_files))

    @api_method
    def renamer_preview(self, params: dict[str, Any]) -> dict[str, Any]:
        # Generate rename plan preview with collisions and proposed paths.
        require(params, "file_paths")
        paths = list(params["file_paths"])

        if "steps" in params:
            steps = list(params.get("steps", []))
            sort_by = str(params.get("sort_by", "name_asc"))
            auto_resolve = bool(params.get("auto_resolve_conflicts", True))
            plans = preview_step_pipeline(
                paths,
                steps,
                sort_by=sort_by,
                auto_resolve_conflicts=auto_resolve,
            )
        else:
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
            entries=[p.to_dict() for p in plans],
            has_conflicts=has_conflicts,
            total_count=len(plans),
        )

    @api_method
    def renamer_execute(self, params: dict[str, Any]) -> dict[str, Any]:
        # Execute batch file renames based on plan.
        require(params, "file_paths")
        paths = list(params["file_paths"])

        if "steps" in params:
            steps = list(params.get("steps", []))
            sort_by = str(params.get("sort_by", "name_asc"))
            auto_resolve = bool(params.get("auto_resolve_conflicts", True))
            plans = preview_step_pipeline(
                paths,
                steps,
                sort_by=sort_by,
                auto_resolve_conflicts=auto_resolve,
            )
        else:
            if params.get("timeline"):
                paths = sort_files_by_timeline(paths)
            mode = str(params.get("mode", "template"))
            plan_params = dict(params.get("options", params))
            plans = preview_renames(paths, mode, plan_params)
            consolidate_dir = str(params.get("consolidate_to", "")).strip()
            if consolidate_dir:
                plans = plan_consolidate_to_folder(plans, consolidate_dir)

        results = execute_renames(plans)
        res_list = [{
            "original": r.old_path,
            "target": r.new_path,
            "success": r.success,
            "error": r.error,
        } for r in results]
        self._last_renamer_results = res_list
        succeeded = sum(1 for r in results if r.success)
        return ok(
            results=res_list,
            renamed_count=succeeded,
            undo_available=(succeeded > 0),
        )

    @api_method
    def renamer_apply(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for executing batch renames.
        return self.renamer_execute(params)

    @api_method
    def renamer_undo(self, params: dict[str, Any]) -> dict[str, Any]:
        # Revert previously executed rename operations safely.
        raw_results = params.get("results")
        if not raw_results:
            raw_results = getattr(self, "_last_renamer_results", [])
        undo_items: list[tuple[str, str]] = []
        for r in raw_results:
            if isinstance(r, dict) and r.get("success"):
                orig = r.get("original")
                target = r.get("target")
                if orig and target and orig != target:
                    undo_items.append((orig, target))
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
        res_list = [{
            "original": r.old_path,
            "target": r.new_path,
            "success": r.success,
            "error": r.error,
        } for r in results]
        succeeded = sum(1 for r in results if r.success)
        self._last_renamer_results = []
        return ok(
            results=res_list,
            restored_count=succeeded,
        )

    @api_method
    def renamer_presets(self, params: dict[str, Any]) -> dict[str, Any]:
        # List, save, or delete persistent plain-English renaming recipes.
        action = str(params.get("action", "list"))
        current_saved = list(get_setting("renamer_recipes", []))

        if action == "save":
            recipe = dict(params.get("recipe", {}))
            name = str(recipe.get("name", "")).strip()
            if not name:
                raise ValueError("Recipe must have a valid name.")
            filtered = [r for r in current_saved if r.get("name") != name]
            filtered.append(recipe)
            set_setting("renamer_recipes", filtered)
            return ok(saved=True, recipes=filtered)

        if action == "delete":
            target_name = str(params.get("name", "")).strip()
            filtered = [r for r in current_saved if r.get("name") != target_name]
            set_setting("renamer_recipes", filtered)
            return ok(deleted=True, recipes=filtered)

        return ok(
            starter_recipes=STARTER_RECIPES,
            user_recipes=current_saved,
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
        return ok(entries=[p.to_dict() for p in consolidated])

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
