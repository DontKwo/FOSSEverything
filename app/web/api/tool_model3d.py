import base64
from typing import Any

import numpy as np

from app.web.api.result import api_method, ok, require


class Model3dApiMixin:
    @api_method
    def model3d_info(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return geometry bounding box, volume, vertex count, and watertight status.
        from app.features.model3d.ops import CAD_INSTALL_HINT, Model3D, info, load

        require(params, "file_path")
        file_path = str(params["file_path"])
        model_data: Model3D = load(file_path)
        stats = info(model_data)
        return ok(info=stats, cad_hint=CAD_INSTALL_HINT, file_path=file_path)

    @api_method
    def model3d_load(self, params: dict[str, Any]) -> dict[str, Any]:
        # Load 3D model and return serialized mesh coordinates.
        from app.features.model3d.ops import info, load, tessellated_preview

        require(params, "file_path")
        file_path = str(params["file_path"])
        model_data = load(file_path)
        stats = info(model_data)
        verts, faces = tessellated_preview(model_data)
        v_bytes = np.asarray(verts, dtype=np.float32).tobytes()
        f_bytes = np.asarray(faces, dtype=np.uint32).tobytes()
        v_b64 = base64.b64encode(v_bytes).decode("ascii")
        f_b64 = base64.b64encode(f_bytes).decode("ascii")
        return ok(
            vertices=v_b64,
            faces=f_b64,
            vertex_count=len(verts),
            face_count=len(faces),
            info=stats,
            file_path=file_path,
        )

    @api_method
    def model3d_load_mesh(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for loading 3D mesh data.
        return self.model3d_load(params)

    @api_method
    def model3d_cut(self, params: dict[str, Any]) -> dict[str, Any]:
        # Slice 3D model across one or more geometric cutting planes.
        from app.features.model3d.ops import cut_multi, export, info, load

        require(params, "file_path", "planes", "output_dir")
        file_path = str(params["file_path"])
        planes_list = list(params["planes"])
        out_dir = str(params["output_dir"])
        cap_solid = bool(params.get("cap", True))
        model_data = load(file_path)
        cuts = [(tuple(item["origin"]), tuple(item["normal"])) for item in planes_list]
        pieces = cut_multi(model_data, cuts, cap=cap_solid)
        results: list[str] = []
        piece_stats: list[dict[str, Any]] = []
        for piece_index, piece in enumerate(pieces):
            piece_path = f"{out_dir}/piece_{piece_index + 1}.stl"
            export(piece, piece_path)
            results.append(piece_path)
            piece_stats.append({
                "piece_index": piece_index + 1,
                "path": piece_path,
                "info": info(piece),
            })
        return ok(pieces=results, count=len(results), details=piece_stats)

    @api_method
    def model3d_cut_mesh(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for cutting mesh.
        return self.model3d_cut(params)

    @api_method
    def model3d_repair(self, params: dict[str, Any]) -> dict[str, Any]:
        # Repair non-manifold edges, invert normals, and fix holes in mesh.
        from app.features.model3d.ops import export, info, load, repair

        require(params, "file_path", "output_path")
        file_path = str(params["file_path"])
        output_path = str(params["output_path"])
        model_data = load(file_path)
        repaired = repair(model_data)
        export(repaired, output_path)
        new_stats = info(repaired)
        return ok(output_path=output_path, info=new_stats)

    @api_method
    def model3d_repair_mesh(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for repairing mesh.
        return self.model3d_repair(params)

    @api_method
    def model3d_scale(self, params: dict[str, Any]) -> dict[str, Any]:
        # Rescale model dimensions by uniform or axis-specific factors.
        from app.features.model3d.ops import export, info, load, scale

        require(params, "file_path", "output_path")
        file_path = str(params["file_path"])
        output_path = str(params["output_path"])
        model_data = load(file_path)
        if "factor_x" in params or "factor_y" in params or "factor_z" in params:
            factor_val = float(params.get("factor", 1.0))
            factor_x = float(params.get("factor_x", factor_val))
            factor_y = float(params.get("factor_y", factor_val))
            factor_z = float(params.get("factor_z", factor_val))
            scaled = scale(model_data, factor_x, factor_y, factor_z)
        else:
            require(params, "factor")
            factor = float(params["factor"])
            scaled = scale(model_data, factor)
        export(scaled, output_path)
        new_stats = info(scaled)
        return ok(output_path=output_path, info=new_stats)

    @api_method
    def model3d_scale_mesh(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for scaling mesh.
        return self.model3d_scale(params)

    @api_method
    def model3d_measure(self, params: dict[str, Any]) -> dict[str, Any]:
        # Calculate Euclidean distance between two selected 3D coordinates.
        from app.features.model3d.ops import measure_distance

        require(params, "p1", "p2")
        point_1 = tuple(float(coord_val) for coord_val in params["p1"])
        point_2 = tuple(float(coord_val) for coord_val in params["p2"])
        measured_distance = measure_distance(point_1, point_2)
        return ok(distance=round(measured_distance, 4))

    @api_method
    def model3d_export(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert and export 3D model to STL, OBJ, or PLY format.
        from app.features.model3d.ops import export, load

        require(params, "file_path", "output_path")
        file_path = str(params["file_path"])
        output_path = str(params["output_path"])
        fmt = params.get("format")
        model_data = load(file_path)
        res_p = export(model_data, output_path, fmt=str(fmt) if fmt else None)
        return ok(output_path=res_p)

    @api_method
    def model3d_center_origin(self, params: dict[str, Any]) -> dict[str, Any]:
        # Re-center geometry at origin (0, 0, 0) and export centered mesh.
        from app.features.model3d.ops import export, info, load

        require(params, "file_path", "output_path")
        file_path = str(params["file_path"])
        output_path = str(params["output_path"])
        model_data = load(file_path)
        if model_data.backend == "mesh" and model_data.mesh is not None:
            center = (model_data.mesh.bounds[0] + model_data.mesh.bounds[1]) / 2.0
            model_data.mesh.apply_translation(-center)
        elif model_data.backend == "brep" and model_data.shape is not None:
            from app.features.model3d import brep_backend
            model_data.shape = brep_backend.brep_center(model_data.shape)
        export(model_data, output_path)
        new_stats = info(model_data)
        return ok(output_path=output_path, info=new_stats)
