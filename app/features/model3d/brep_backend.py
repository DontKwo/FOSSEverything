"""OpenCASCADE (OCP) backend for STEP/IGES BREP geometry.

Every OCP import lives inside a function body, never at module scope, so a
broken or missing install of the optional `cadquery-ocp` package can never
prevent `app.features.model3d.ops` (and therefore the rest of the app) from
importing successfully.
"""
from __future__ import annotations

from typing import Any

import numpy as np


def brep_load(path: str) -> Any:
    """Read a STEP or IGES file and return its top-level TopoDS_Shape."""
    from OCP.IFSelect import IFSelect_RetDone

    lower = path.lower()
    if lower.endswith(".iges") or lower.endswith(".igs"):
        from OCP.IGESControl import IGESControl_Reader
        reader = IGESControl_Reader()
    else:
        from OCP.STEPControl import STEPControl_Reader
        reader = STEPControl_Reader()

    status = reader.ReadFile(path)
    if status != IFSelect_RetDone:
        raise ValueError(f"Could not read CAD file: {path}")
    reader.TransferRoots()
    return reader.OneShape()


def brep_cut(shape: Any, plane_point: np.ndarray, plane_normal: np.ndarray, cap: bool = True) -> tuple[Any, Any]:
    """Cut *shape* with an infinite plane, returning (positive_side, negative_side) shapes.

    *cap* only exists for interface symmetry with the mesh backend and is ignored:
    OCCT solids are always topologically closed, so a BREP cut is inherently capped.
    """
    from OCP.gp import gp_Dir, gp_Pln, gp_Pnt
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeHalfSpace
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib

    bbox = Bnd_Box()
    BRepBndLib.Add_s(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    diag = float(np.linalg.norm([xmax - xmin, ymax - ymin, zmax - zmin]))
    far = max(diag * 10.0, 1.0)

    plane = gp_Pln(gp_Pnt(*[float(v) for v in plane_point]), gp_Dir(*[float(v) for v in plane_normal]))
    face = BRepBuilderAPI_MakeFace(plane).Face()

    seed_neg = plane_point - plane_normal * far
    seed_pos = plane_point + plane_normal * far
    half_pos = BRepPrimAPI_MakeHalfSpace(face, gp_Pnt(*[float(v) for v in seed_neg])).Solid()
    half_neg = BRepPrimAPI_MakeHalfSpace(face, gp_Pnt(*[float(v) for v in seed_pos])).Solid()

    try:
        piece_a = BRepAlgoAPI_Common(shape, half_pos).Shape()
        piece_b = BRepAlgoAPI_Common(shape, half_neg).Shape()
    except Exception as exc:
        raise RuntimeError(
            "This STEP/IGES geometry could not be cut cleanly at this plane. Try nudging the plane slightly."
        ) from exc
    return piece_a, piece_b


def brep_is_valid(shape: Any) -> bool:
    from OCP.BRepCheck import BRepCheck_Analyzer
    return bool(BRepCheck_Analyzer(shape).IsValid())


def brep_is_empty(shape: Any, tol: float = 1e-9) -> bool:
    """True if *shape* has no material left (e.g. a plane missed it entirely)."""
    if shape.IsNull():
        return True
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib

    bbox = Bnd_Box()
    BRepBndLib.Add_s(shape, bbox)
    if bbox.IsVoid():
        return True
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    return max(xmax - xmin, ymax - ymin, zmax - zmin) < tol


def brep_shape_kind(shape: Any) -> str:
    """Return 'solid', 'shell', or 'other' describing the shape's top-level topology."""
    from OCP.TopAbs import TopAbs_COMPOUND, TopAbs_SHELL, TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer

    kind = shape.ShapeType()
    if kind == TopAbs_SOLID:
        return "solid"
    if kind == TopAbs_SHELL:
        return "shell"
    if kind == TopAbs_COMPOUND:
        explorer = TopExp_Explorer(shape, TopAbs_SOLID)
        return "solid" if explorer.More() else "shell"
    return "other"


def brep_tessellate(shape: Any, linear_deflection: float = 0.5) -> tuple[np.ndarray, np.ndarray]:
    """Tessellate *shape* into (vertices, faces) float32/int32 numpy arrays."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS

    BRepMesh_IncrementalMesh(shape, linear_deflection)
    verts: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = TopoDS.Face_s(explorer.Current())
        loc = TopLoc_Location()
        triangulation = BRep_Tool.Triangulation_s(face, loc)
        if triangulation is not None:
            offset = len(verts)
            trsf = loc.Transformation()
            for i in range(1, triangulation.NbNodes() + 1):
                p = triangulation.Node(i).Transformed(trsf)
                verts.append((p.X(), p.Y(), p.Z()))
            for i in range(1, triangulation.NbTriangles() + 1):
                tri = triangulation.Triangle(i)
                a, b, c = tri.Get()
                faces.append((offset + a - 1, offset + b - 1, offset + c - 1))
        explorer.Next()
    return np.array(verts, dtype=np.float32), np.array(faces, dtype=np.int32)


def brep_export_step(shape: Any, path: str) -> None:
    from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    writer.Write(path)


def brep_export_iges(shape: Any, path: str) -> None:
    from OCP.IGESControl import IGESControl_Writer
    writer = IGESControl_Writer()
    writer.AddShape(shape)
    writer.Write(path)


def brep_scale(shape: Any, factor: float) -> Any:
    """Uniformly scale *shape* about the origin, returning a new shape."""
    from OCP.gp import gp_Pnt, gp_Trsf
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform

    trsf = gp_Trsf()
    trsf.SetScale(gp_Pnt(0.0, 0.0, 0.0), factor)
    return BRepBuilderAPI_Transform(shape, trsf, True).Shape()


def mesh_to_brep(vertices: np.ndarray, faces: np.ndarray, watertight: bool) -> Any:
    """Build a faceted (planar-triangle) BREP shell/solid from a triangle mesh."""
    from OCP.gp import gp_Pnt
    from OCP.BRepBuilderAPI import (
        BRepBuilderAPI_MakeFace,
        BRepBuilderAPI_MakePolygon,
        BRepBuilderAPI_MakeSolid,
        BRepBuilderAPI_Sewing,
    )
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.TopoDS import TopoDS

    sewing = BRepBuilderAPI_Sewing(1e-6)
    for tri in faces:
        poly = BRepBuilderAPI_MakePolygon()
        for vertex_index in tri:
            x, y, z = vertices[vertex_index]
            poly.Add(gp_Pnt(float(x), float(y), float(z)))
        poly.Close()
        face = BRepBuilderAPI_MakeFace(poly.Wire()).Face()
        sewing.Add(face)
    sewing.Perform()
    shell = sewing.SewedShape()

    if watertight and shell.ShapeType() == TopAbs_SHELL:
        try:
            solid_maker = BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(shell))
            if solid_maker.IsDone():
                return solid_maker.Solid()
        except Exception:  # noqa: 10 (best-effort solid upgrade; the shell fallback below is intentional)
            pass
    return shell
