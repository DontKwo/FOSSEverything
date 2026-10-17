"""Headless domain logic for 3D model geometry: load, cut-plane, repair, scale, export.

No Qt imports here - this module is usable and testable standalone. STEP/IGES
support depends on the optional `cadquery-ocp` package (the `[cad]` extra);
when it's missing, only STL/OBJ/PLY mesh operations are available and
`brep_backend_available()` reports False so callers can degrade gracefully.
"""
from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
import trimesh

from app.core.file_formats import normalized_format

MESH_EXTENSIONS = {".stl", ".obj", ".ply"}
BREP_EXTENSIONS = {".step", ".stp", ".iges", ".igs"}
MODEL3D_EXTENSIONS = MESH_EXTENSIONS | BREP_EXTENSIONS

CAD_INSTALL_HINT = "STEP/IGES support requires the optional CAD backend. Install it with: pip install -e .[cad]"


@dataclass
class Model3D:
    """A loaded 3D model, backed by either a trimesh mesh or an OCP BREP shape."""

    backend: Literal["mesh", "brep"]
    mesh: Any = None                 # trimesh.Trimesh, when backend == "mesh"
    shape: Any = None                # OCP TopoDS_Shape, when backend == "brep"
    source_path: str | None = None
    source_format: str | None = None
    warnings: list[str] = field(default_factory=list)
    preview_cache: Any = field(default=None, repr=False, compare=False)


def brep_backend_available() -> bool:
    """Cheap probe for the optional CAD backend; never raises."""
    try:
        return importlib.util.find_spec("OCP") is not None
    except Exception:
        return False


def load(path: str) -> Model3D:
    """Load an STL/OBJ/PLY mesh or a STEP/IGES BREP model from *path*."""
    ext = os.path.splitext(path)[1].lower()
    if ext in BREP_EXTENSIONS:
        if not brep_backend_available():
            raise RuntimeError(CAD_INSTALL_HINT)
        from app.features.model3d import brep_backend
        shape = brep_backend.brep_load(path)
        return Model3D(backend="brep", shape=shape, source_path=path, source_format=normalized_format(ext))
    if ext in MESH_EXTENSIONS:
        mesh = trimesh.load(path, force="mesh")
        return Model3D(backend="mesh", mesh=mesh, source_path=path, source_format=normalized_format(ext))
    raise ValueError(f"Unsupported 3D model format: {ext}")


def info(model: Model3D) -> dict:
    """Return volume/area/watertight/bbox/counts for *model*."""
    if model.backend == "mesh":
        mesh = model.mesh
        return {
            "backend": "mesh",
            "watertight": bool(mesh.is_watertight),
            "volume": float(mesh.volume) if mesh.is_watertight else None,
            "surface_area": float(mesh.area),
            "bbox_min": mesh.bounds[0].tolist(),
            "bbox_max": mesh.bounds[1].tolist(),
            "triangle_count": int(len(mesh.faces)),
            "vertex_count": int(len(mesh.vertices)),
        }

    from app.features.model3d import brep_backend
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    shape = model.shape
    kind = brep_backend.brep_shape_kind(shape)
    volume = None
    if kind == "solid":
        volume_props = GProp_GProps()
        BRepGProp.VolumeProperties_s(shape, volume_props)
        volume = float(volume_props.Mass())
    surface_props = GProp_GProps()
    BRepGProp.SurfaceProperties_s(shape, surface_props)
    bbox = Bnd_Box()
    BRepBndLib.Add_s(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    return {
        "backend": "brep",
        "watertight": kind == "solid",
        "volume": volume,
        "surface_area": float(surface_props.Mass()),
        "bbox_min": [xmin, ymin, zmin],
        "bbox_max": [xmax, ymax, zmax],
        "triangle_count": None,
        "vertex_count": None,
    }


def tessellated_preview(model: Model3D, linear_deflection: float = 0.5) -> tuple[np.ndarray, np.ndarray]:
    """Return (vertices, faces) float32/int32 numpy arrays for rendering *model*."""
    if model.backend == "mesh":
        return model.mesh.vertices.astype(np.float32), model.mesh.faces.astype(np.int32)
    if model.preview_cache is not None:
        return model.preview_cache
    from app.features.model3d import brep_backend
    verts, faces = brep_backend.brep_tessellate(model.shape, linear_deflection)
    model.preview_cache = (verts, faces)
    return verts, faces


def cut(
    model: Model3D,
    plane_point: tuple[float, float, float],
    plane_normal: tuple[float, float, float],
    cap: bool = True,
) -> tuple[Model3D, Model3D]:
    """Cut *model* with a plane, returning the two resulting pieces as new Model3D instances."""
    normal = np.array(plane_normal, dtype=float)
    norm_len = np.linalg.norm(normal)
    if norm_len == 0:
        raise ValueError("Cut plane normal cannot be a zero vector.")
    normal = normal / norm_len
    origin = np.array(plane_point, dtype=float)

    if model.backend == "mesh":
        return _mesh_cut(model, origin, normal, cap)

    from app.features.model3d import brep_backend
    piece_a_shape, piece_b_shape = brep_backend.brep_cut(model.shape, origin, normal, cap)
    warnings = list(model.warnings)
    for label, piece in (("first", piece_a_shape), ("second", piece_b_shape)):
        if not brep_backend.brep_is_valid(piece):
            warnings.append(f"The {label} cut piece failed OCCT validity checks; it may have geometric defects.")
    piece_a = Model3D(backend="brep", shape=piece_a_shape, source_format=model.source_format, warnings=warnings)
    piece_b = Model3D(backend="brep", shape=piece_b_shape, source_format=model.source_format, warnings=warnings)
    return piece_a, piece_b


def _is_empty(piece: Model3D) -> bool:
    """True if a cut plane missed *piece* entirely, leaving it with no material."""
    if piece.backend == "mesh":
        return piece.mesh is None or len(piece.mesh.faces) == 0
    if piece.shape is None:
        return True
    from app.features.model3d import brep_backend
    return brep_backend.brep_is_empty(piece.shape)


def cut_multi(
    model: Model3D,
    planes: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    cap: bool = True,
) -> list[Model3D]:
    """Cut *model* with one or more planes, returning every resulting non-empty piece.

    Each additional plane cuts every piece produced so far, so N planes yield up
    to 2**N pieces (fewer whenever a plane misses a given piece entirely).
    """
    if not planes:
        raise ValueError("At least one cutting plane is required.")
    pieces = [model]
    for origin, normal in planes:
        next_pieces = []
        for piece in pieces:
            piece_a, piece_b = cut(piece, origin, normal, cap=cap)
            next_pieces.extend(p for p in (piece_a, piece_b) if not _is_empty(p))
        pieces = next_pieces
    if not pieces:
        raise ValueError("The cutting planes removed the entire model; adjust plane placement.")
    return pieces


def _mesh_cut(model: Model3D, origin: np.ndarray, normal: np.ndarray, cap: bool) -> tuple[Model3D, Model3D]:
    mesh = model.mesh
    warnings = list(model.warnings)
    if cap and not mesh.is_watertight:
        repaired = mesh.copy()
        trimesh.repair.fill_holes(repaired)
        trimesh.repair.fix_normals(repaired)
        if repaired.is_watertight:
            mesh = repaired
            warnings.append("Source mesh was not watertight; holes were auto-repaired before capping.")
        else:
            warnings.append("Source mesh is not watertight and could not be auto-repaired; the cap may be incomplete.")

    def _slice(sign: float) -> trimesh.Trimesh:
        try:
            return mesh.slice_plane(origin, normal * sign, cap=cap)
        except Exception:
            return mesh.slice_plane(origin, normal * sign, cap=False)

    piece_a = _slice(1.0)
    piece_b = _slice(-1.0)
    return (
        Model3D(backend="mesh", mesh=piece_a, source_format=model.source_format, warnings=warnings),
        Model3D(backend="mesh", mesh=piece_b, source_format=model.source_format, warnings=warnings),
    )


def repair(model: Model3D) -> Model3D:
    """Fill holes, remove duplicate/degenerate faces, and fix normals on a mesh model."""
    if model.backend != "mesh":
        raise ValueError("Repair is only available for mesh (STL/OBJ/PLY) models.")
    mesh = model.mesh.copy()
    trimesh.repair.fill_holes(mesh)
    mesh.update_faces(mesh.unique_faces())
    mesh.update_faces(mesh.nondegenerate_faces())
    trimesh.repair.fix_normals(mesh)
    return Model3D(backend="mesh", mesh=mesh, source_path=model.source_path, source_format=model.source_format, warnings=list(model.warnings))


def scale(model: Model3D, factor_x: float, factor_y: float | None = None, factor_z: float | None = None) -> Model3D:
    """Scale *model* by the given per-axis factors (uniform if only factor_x is given)."""
    fy = factor_y if factor_y is not None else factor_x
    fz = factor_z if factor_z is not None else factor_x
    if model.backend == "mesh":
        mesh = model.mesh.copy()
        mesh.apply_scale((factor_x, fy, fz))
        return Model3D(backend="mesh", mesh=mesh, source_path=model.source_path, source_format=model.source_format, warnings=list(model.warnings))
    if fy != factor_x or fz != factor_x:
        raise ValueError("Non-uniform scale is only supported for mesh (STL/OBJ/PLY) models.")
    from app.features.model3d import brep_backend
    shape = brep_backend.brep_scale(model.shape, factor_x)
    return Model3D(backend="brep", shape=shape, source_path=model.source_path, source_format=model.source_format, warnings=list(model.warnings))


def measure_distance(point_a: tuple[float, float, float], point_b: tuple[float, float, float]) -> float:
    """Straight-line distance between two picked points, in the model's own units."""
    return float(np.linalg.norm(np.array(point_a) - np.array(point_b)))


def export(model: Model3D, path: str, fmt: str | None = None) -> str:
    """Export *model* to *path*, converting between mesh and BREP formats as needed."""
    target = normalized_format(fmt) if fmt else normalized_format(os.path.splitext(path)[1])

    if target in ("STEP", "IGES"):
        if not brep_backend_available():
            raise RuntimeError(CAD_INSTALL_HINT)
        from app.features.model3d import brep_backend
        if model.backend == "brep":
            shape = model.shape
        else:
            verts, faces = tessellated_preview(model)
            shape = brep_backend.mesh_to_brep(verts, faces, bool(model.mesh.is_watertight))
        if target == "STEP":
            brep_backend.brep_export_step(shape, path)
        else:
            brep_backend.brep_export_iges(shape, path)
        return path

    if model.backend == "brep":
        from app.features.model3d import brep_backend
        verts, faces = brep_backend.brep_tessellate(model.shape)
        mesh = trimesh.Trimesh(vertices=verts, faces=faces)
    else:
        mesh = model.mesh
    mesh.export(path, file_type=target.lower())
    return path
