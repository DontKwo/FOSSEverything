import base64
from typing import Any

import numpy as np

from app.features.model3d.ops import (
    CAD_INSTALL_HINT,
    Model3D,
    cut_multi,
    export,
    info,
    load,
    measure_distance,
    repair,
    scale,
    tessellated_preview,
)
from app.web.api.result import api_method, ok, require


class Model3dApiMixin:
    @api_method
    def model3d_info(self, params: dict[str, Any]) -> dict[str, Any]:
        # Return geometry bounding box, volume, vertex count, and watertight status.
        require(params, "file_path")
        file_path = str(params["file_path"])
        m3d: Model3D = load(file_path)
        stats = info(m3d)
        return ok(info=stats, cad_hint=CAD_INSTALL_HINT, file_path=file_path)

    @api_method
    def model3d_load(self, params: dict[str, Any]) -> dict[str, Any]:
        # Load 3D model and return serialized mesh coordinates.
        require(params, "file_path")
        file_path = str(params["file_path"])
        m3d = load(file_path)
        stats = info(m3d)
        verts, faces = tessellated_preview(m3d)
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
        require(params, "file_path", "planes", "output_dir")
        file_path = str(params["file_path"])
        planes = list(params["planes"])
        out_dir = str(params["output_dir"])
        m3d = load(file_path)
        cuts = [(tuple(p["origin"]), tuple(p["normal"])) for p in planes]
        pieces = cut_multi(m3d, cuts)
        results: list[str] = []
        for i, piece in enumerate(pieces):
            out_p = f"{out_dir}/piece_{i+1}.stl"
            export(piece, out_p)
            results.append(out_p)
        return ok(pieces=results, count=len(results))

    @api_method
    def model3d_cut_mesh(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for cutting mesh.
        return self.model3d_cut(params)

    @api_method
    def model3d_repair(self, params: dict[str, Any]) -> dict[str, Any]:
        # Repair non-manifold edges, invert normals, and fix holes in mesh.
        require(params, "file_path", "output_path")
        file_path = str(params["file_path"])
        out_p = str(params["output_path"])
        m3d = load(file_path)
        repaired = repair(m3d)
        export(repaired, out_p)
        new_stats = info(repaired)
        return ok(output_path=out_p, info=new_stats)

    @api_method
    def model3d_repair_mesh(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for repairing mesh.
        return self.model3d_repair(params)

    @api_method
    def model3d_scale(self, params: dict[str, Any]) -> dict[str, Any]:
        # Rescale model dimensions by uniform or axis-specific factors.
        require(params, "file_path", "factor", "output_path")
        file_path = str(params["file_path"])
        factor = float(params["factor"])
        out_p = str(params["output_path"])
        m3d = load(file_path)
        scaled = scale(m3d, factor)
        export(scaled, out_p)
        new_stats = info(scaled)
        return ok(output_path=out_p, info=new_stats)

    @api_method
    def model3d_scale_mesh(self, params: dict[str, Any]) -> dict[str, Any]:
        # Alias for scaling mesh.
        return self.model3d_scale(params)

    @api_method
    def model3d_measure(self, params: dict[str, Any]) -> dict[str, Any]:
        # Calculate Euclidean distance between two selected 3D coordinates.
        require(params, "p1", "p2")
        p1 = tuple(float(v) for v in params["p1"])
        p2 = tuple(float(v) for v in params["p2"])
        dist = measure_distance(p1, p2)
        return ok(distance=round(dist, 4))

    @api_method
    def model3d_export(self, params: dict[str, Any]) -> dict[str, Any]:
        # Convert and export 3D model to STL, OBJ, or PLY format.
        require(params, "file_path", "output_path")
        file_path = str(params["file_path"])
        out_p = str(params["output_path"])
        fmt = params.get("format")
        m3d = load(file_path)
        res_p = export(m3d, out_p, fmt=str(fmt) if fmt else None)
        return ok(output_path=res_p)

    @api_method
    def model3d_center_origin(self, params: dict[str, Any]) -> dict[str, Any]:
        # Re-center geometry at origin (0, 0, 0) and export centered mesh.
        require(params, "file_path", "output_path")
        file_path = str(params["file_path"])
        out_p = str(params["output_path"])
        m3d = load(file_path)
        if m3d.backend == "mesh" and m3d.mesh is not None:
            center = (m3d.mesh.bounds[0] + m3d.mesh.bounds[1]) / 2.0
            m3d.mesh.apply_translation(-center)
        export(m3d, out_p)
        new_stats = info(m3d)
        return ok(output_path=out_p, info=new_stats)
