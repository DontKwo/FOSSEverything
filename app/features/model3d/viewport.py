"""Interactive 3D viewport built on PyVista/VTK (via pyvistaqt). Replaces a
former hand-rolled QOpenGLWidget camera that lacked arcball rotation, zoom-to-
cursor, and DPI-aware sensitivity - VTK's trackball camera and surface point
picking are mature and free."""
from __future__ import annotations

import threading
from typing import Any

import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

# pyvista/vtk take 1-3s to import the first time; _load_vtk_stack() runs on a
# background thread (see preload_vtk_stack_in_background) and caches the result here.
_vtk_stack: dict[str, Any] = {}
_vtk_stack_lock = threading.Lock()


def _load_vtk_stack() -> None:
    with _vtk_stack_lock:
        if _vtk_stack:
            return
        import pyvista as pv
        from pyvistaqt import QtInteractor
        from vtkmodules.vtkRenderingCore import vtkCellPicker
        _vtk_stack.update(pv=pv, QtInteractor=QtInteractor, vtkCellPicker=vtkCellPicker)


def preload_vtk_stack_in_background() -> None:
    """Start importing pyvista/vtk on a daemon thread. Safe to call more than
    once (or before this module's widgets are ever used) - a no-op if already
    loaded or already loading."""
    if _vtk_stack or _vtk_stack_lock.locked():
        return
    threading.Thread(target=_load_vtk_stack, daemon=True).start()


_PALETTE: tuple[tuple[float, float, float], ...] = (
    (0.65, 0.68, 0.75),
    (0.55, 0.75, 0.60),
    (0.75, 0.65, 0.55),
    (0.62, 0.58, 0.78),
    (0.55, 0.72, 0.78),
    (0.78, 0.55, 0.62),
)
_HIGHLIGHT_COLOR = (0.95, 0.75, 0.20)
_PLANE_COLOR = (0.95, 0.55, 0.15)
# Scales raw mouse-drag deltas down so a full-screen drag doesn't fling the
# plane across the whole model or spin it multiple full turns.
_GIZMO_DRAG_SENSITIVITY = 0.2
# Translate-arrow / rotate-arc colors, one per local plane axis (U, V, N).
_AXIS_COLORS: tuple[tuple[float, float, float], ...] = (
    (0.85, 0.25, 0.25),
    (0.25, 0.75, 0.30),
    (0.25, 0.45, 0.90),
)


def _to_polydata(pv: Any, vertices: np.ndarray, faces: np.ndarray) -> Any:
    face_count = len(faces)
    connectivity = np.hstack(
        [np.full((face_count, 1), 3, dtype=np.int64), faces.astype(np.int64)]
    ).ravel()
    return pv.PolyData(vertices.astype(np.float64), connectivity)


def _orthonormal_frame(normal: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build an arbitrary (U, V, N) right-handed frame with N along *normal*."""
    norm_len = np.linalg.norm(normal)
    n = normal / norm_len if norm_len > 1e-9 else np.array([0.0, 0.0, 1.0])
    helper = np.array([0.0, 0.0, 1.0]) if abs(n[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(helper, n)
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    return u, v, n


def _rotate_vector(vector: np.ndarray, axis: np.ndarray, angle: float) -> np.ndarray:
    """Rodrigues' rotation formula: rotate *vector* by *angle* radians around *axis*."""
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    return vector * cos_a + np.cross(axis, vector) * sin_a + axis * np.dot(axis, vector) * (1.0 - cos_a)


def _arc_points(center: np.ndarray, axis_a: np.ndarray, axis_b: np.ndarray, radius: float) -> np.ndarray:
    t = np.linspace(0.0, np.pi / 2, 24)
    return center + radius * (np.outer(np.cos(t), axis_a) + np.outer(np.sin(t), axis_b))


class Model3DViewport(QWidget):
    """Renders the active model piece(s) and the current cut-plane gizmo(s)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._placeholder: QLabel | None = QLabel("Loading 3D engine...")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._placeholder)

        self.plotter: Any = None
        self._pv: Any = None
        self._vtk_cell_picker_cls: Any = None
        self._pending_calls: list[Any] = []

        self.on_click = None
        self._actors: list[Any] = []
        self._actor_colors: list[tuple[float, float, float]] = []
        self._plane_actors: list[Any] = []
        self._bounds_diag = 10.0

        # Draggable/rotatable cut-plane gizmo state.
        self._gizmo_actors: list[Any] = []
        self._gizmo_actor_map: dict[Any, tuple[str, int]] = {}
        self._gizmo_origin: np.ndarray | None = None
        self._gizmo_axes: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None
        self._gizmo_callback: Any = None
        self._gizmo_observers: list[int] = []
        self._gizmo_drag: dict[str, Any] | None = None
        self._gizmo_saved_style: Any = None

        preload_vtk_stack_in_background()
        self._ready_poll = QTimer(self)
        self._ready_poll.setInterval(50)
        self._ready_poll.timeout.connect(self._check_engine_ready)
        self._ready_poll.start()

    def _check_engine_ready(self) -> None:
        if not _vtk_stack:
            return
        self._ready_poll.stop()
        self._pv = _vtk_stack["pv"]
        self._vtk_cell_picker_cls = _vtk_stack["vtkCellPicker"]
        self.plotter = _vtk_stack["QtInteractor"](self)
        self._layout.removeWidget(self._placeholder)
        self._placeholder.deleteLater()
        self._placeholder = None
        self._layout.addWidget(self.plotter.interactor)

        pending, self._pending_calls = self._pending_calls, []
        for call in pending:
            call()

    def _is_ready(self) -> bool:
        return self.plotter is not None

    # ─── Public API ──────────────────────────────────────────────────────

    def set_models(self, meshes: list[tuple[np.ndarray, np.ndarray]]) -> None:
        """Replace all displayed pieces. Each piece gets a distinct palette color."""
        if not self._is_ready():
            self._pending_calls.append(lambda: self.set_models(meshes))
            return
        for actor in self._actors:
            self.plotter.remove_actor(actor)
        self._actors = []
        self._actor_colors = []
        self.disable_plane_widget()

        all_vertices = []
        for index, (vertices, faces) in enumerate(meshes):
            mesh = _to_polydata(self._pv, vertices, faces)
            color = _PALETTE[index % len(_PALETTE)]
            actor = self.plotter.add_mesh(mesh, color=color, smooth_shading=True, pickable=True)
            self._actors.append(actor)
            self._actor_colors.append(color)
            all_vertices.append(vertices)

        if all_vertices:
            self._fit_camera_to(np.concatenate(all_vertices, axis=0))
        self.plotter.reset_camera()

    def highlight_model(self, index: int | None) -> None:
        """Recolor the piece at *index* to stand out; None resets all to palette colors."""
        if not self._is_ready():
            self._pending_calls.append(lambda: self.highlight_model(index))
            return
        for i, actor in enumerate(self._actors):
            actor.prop.color = _HIGHLIGHT_COLOR if i == index else self._actor_colors[i]

    def set_cut_planes(self, planes: list[tuple[tuple[float, float, float], tuple[float, float, float]]]) -> None:
        if not self._is_ready():
            self._pending_calls.append(lambda: self.set_cut_planes(planes))
            return
        for actor in self._plane_actors:
            self.plotter.remove_actor(actor)
        self._plane_actors = []
        size = self._bounds_diag * 1.5
        for origin, normal in planes:
            n = np.array(normal, dtype=float)
            norm_len = np.linalg.norm(n)
            if not norm_len:
                continue
            plane = self._pv.Plane(center=np.array(origin, dtype=float), direction=n / norm_len, i_size=size, j_size=size)
            actor = self.plotter.add_mesh(plane, color=_PLANE_COLOR, opacity=0.35, pickable=False)
            self._plane_actors.append(actor)

    def enable_plane_widget(self, origin: tuple[float, float, float], normal: tuple[float, float, float], callback: Any) -> None:
        """Show a SolidWorks-style move/rotate gizmo at *origin*: three arrows
        translate along the plane's local axes, three curved handles rotate
        around them, and a translucent quad previews the plane itself."""
        if not self._is_ready():
            self._pending_calls.append(lambda: self.enable_plane_widget(origin, normal, callback))
            return
        self.disable_plane_widget()
        if not self._actors:
            return
        self._gizmo_origin = np.array(origin, dtype=float)
        self._gizmo_axes = _orthonormal_frame(np.array(normal, dtype=float))
        self._gizmo_callback = callback
        self._build_gizmo_actors()
        interactor = self.plotter.iren.interactor
        self._gizmo_observers = [
            interactor.AddObserver("LeftButtonPressEvent", self._gizmo_on_press),
            interactor.AddObserver("MouseMoveEvent", self._gizmo_on_move),
            interactor.AddObserver("LeftButtonReleaseEvent", self._gizmo_on_release),
        ]

    def disable_plane_widget(self) -> None:
        if not self._is_ready():
            self._pending_calls.append(self.disable_plane_widget)
            return
        interactor = self.plotter.iren.interactor
        for observer_id in self._gizmo_observers:
            interactor.RemoveObserver(observer_id)
        self._gizmo_observers = []
        self._clear_gizmo_actors()
        self._gizmo_origin = None
        self._gizmo_axes = None
        self._gizmo_callback = None
        self._gizmo_drag = None
        self._gizmo_saved_style = None

    def camera_forward(self) -> tuple[float, float, float]:
        if not self._is_ready():
            return (0.0, 0.0, 1.0)
        dx, dy, dz = self.plotter.camera.direction
        return (float(dx), float(dy), float(dz))

    def start_picking(self) -> None:
        """Arm one-shot left-click picking on the visible mesh surface."""
        if not self._is_ready():
            self._pending_calls.append(self.start_picking)
            return
        self.plotter.enable_surface_point_picking(
            callback=self._handle_pick, show_message=False, show_point=False, left_clicking=True,
        )

    def stop_picking(self) -> None:
        if not self._is_ready():
            return
        self.plotter.disable_picking()

    def _handle_pick(self, point: Any) -> None:
        self.stop_picking()
        if self.on_click is not None:
            self.on_click(tuple(float(v) for v in point))

    def _clear_gizmo_actors(self) -> None:
        for actor in self._gizmo_actors:
            self.plotter.remove_actor(actor)
        self._gizmo_actors = []
        self._gizmo_actor_map = {}

    def _build_gizmo_actors(self) -> None:
        self._clear_gizmo_actors()
        origin = self._gizmo_origin
        axes = self._gizmo_axes
        length = max(self._bounds_diag * 0.3, 1e-3)

        plane_size = self._bounds_diag * 1.5
        preview = self._pv.Plane(center=origin, direction=axes[2], i_size=plane_size, j_size=plane_size)
        self._gizmo_actors.append(self.plotter.add_mesh(preview, color=_PLANE_COLOR, opacity=0.3, pickable=False))

        for index, axis in enumerate(axes):
            arrow = self._pv.Arrow(start=origin, direction=axis, scale=length)
            actor = self.plotter.add_mesh(arrow, color=_AXIS_COLORS[index], pickable=True)
            self._gizmo_actors.append(actor)
            self._gizmo_actor_map[actor] = ("translate", index)

        arc_radius = length * 0.85
        tube_radius = length * 0.02
        for axis_a, axis_b, rotate_axis in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
            points = _arc_points(origin, axes[axis_a], axes[axis_b], arc_radius)
            tube = self._pv.lines_from_points(points).tube(radius=tube_radius)
            actor = self.plotter.add_mesh(tube, color=_AXIS_COLORS[rotate_axis], pickable=True)
            self._gizmo_actors.append(actor)
            self._gizmo_actor_map[actor] = ("rotate", rotate_axis)

    def _unproject_at_depth(self, x: int, y: int, ref_point: np.ndarray) -> np.ndarray:
        """Map a screen point to world space, at the depth of *ref_point*."""
        renderer = self.plotter.renderer
        renderer.SetWorldPoint(float(ref_point[0]), float(ref_point[1]), float(ref_point[2]), 1.0)
        renderer.WorldToDisplay()
        _, _, depth = renderer.GetDisplayPoint()
        renderer.SetDisplayPoint(float(x), float(y), depth)
        renderer.DisplayToWorld()
        wx, wy, wz, w = renderer.GetWorldPoint()
        if w:
            wx, wy, wz = wx / w, wy / w, wz / w
        return np.array([wx, wy, wz])

    def _gizmo_on_press(self, _obj: Any, _event: str) -> None:
        if self._gizmo_axes is None:
            return
        x, y = self.plotter.iren.get_event_position()
        picker = self._vtk_cell_picker_cls()
        picker.SetTolerance(0.005)
        for actor in self._gizmo_actors:
            picker.AddPickList(actor)
        picker.PickFromListOn()
        hit = picker.Pick(x, y, 0, self.plotter.renderer)
        actor = picker.GetActor()
        if not hit or actor not in self._gizmo_actor_map:
            return

        kind, index = self._gizmo_actor_map[actor]
        pick_point = np.array(picker.GetPickPosition())
        origin0 = self._gizmo_origin.copy()
        if kind == "translate":
            axis = self._gizmo_axes[index]
            t0 = float(np.dot(pick_point - origin0, axis))
            self._gizmo_drag = {"kind": "translate", "axis": axis, "origin0": origin0, "t0": t0}
        else:
            axis_a, axis_b = (i for i in range(3) if i != index)
            axis = self._gizmo_axes[index]
            vec = pick_point - origin0
            vec = vec - np.dot(vec, axis) * axis
            angle0 = float(np.arctan2(np.dot(vec, self._gizmo_axes[axis_b]), np.dot(vec, self._gizmo_axes[axis_a])))
            self._gizmo_drag = {
                "kind": "rotate",
                "axis": axis,
                "axis_a": axis_a,
                "axis_b": axis_b,
                "origin0": origin0,
                "start_axes": tuple(a.copy() for a in self._gizmo_axes),
                "angle0": angle0,
            }

        # Suspend the trackball style during the drag; our observers are on the
        # raw interactor so they (incl. LeftButtonReleaseEvent) still fire without it.
        self._gizmo_saved_style = self.plotter.iren.interactor.GetInteractorStyle()
        self.plotter.iren.interactor.SetInteractorStyle(None)

    def _gizmo_on_move(self, _obj: Any, _event: str) -> None:
        drag = self._gizmo_drag
        if drag is None:
            return
        x, y = self.plotter.iren.get_event_position()
        point = self._unproject_at_depth(x, y, drag["origin0"])

        if drag["kind"] == "translate":
            t = float(np.dot(point - drag["origin0"], drag["axis"]))
            delta_t = (t - drag["t0"]) * _GIZMO_DRAG_SENSITIVITY
            self._gizmo_origin = drag["origin0"] + delta_t * drag["axis"]
        else:
            vec = point - drag["origin0"]
            vec = vec - np.dot(vec, drag["axis"]) * drag["axis"]
            if np.linalg.norm(vec) < 1e-9:
                return
            start_axes = drag["start_axes"]
            axis_a, axis_b = drag["axis_a"], drag["axis_b"]
            angle = float(np.arctan2(np.dot(vec, start_axes[axis_b]), np.dot(vec, start_axes[axis_a])))
            delta = (angle - drag["angle0"]) * _GIZMO_DRAG_SENSITIVITY
            new_axes = list(start_axes)
            new_axes[axis_a] = _rotate_vector(start_axes[axis_a], drag["axis"], delta)
            new_axes[axis_b] = _rotate_vector(start_axes[axis_b], drag["axis"], delta)
            self._gizmo_axes = tuple(new_axes)

        self._build_gizmo_actors()
        self._emit_gizmo_change()
        self.plotter.render()

    def _gizmo_on_release(self, _obj: Any, _event: str) -> None:
        if self._gizmo_drag is None:
            return
        self._gizmo_drag = None
        if self._gizmo_saved_style is not None:
            self.plotter.iren.interactor.SetInteractorStyle(self._gizmo_saved_style)
            self._gizmo_saved_style = None

    def _emit_gizmo_change(self) -> None:
        if self._gizmo_callback is None:
            return
        normal = tuple(float(v) for v in self._gizmo_axes[2])
        origin = tuple(float(v) for v in self._gizmo_origin)
        self._gizmo_callback(normal, origin)

    def _fit_camera_to(self, vertices: np.ndarray) -> None:
        if len(vertices) == 0:
            return
        mins = vertices.min(axis=0)
        maxs = vertices.max(axis=0)
        diag = float(np.linalg.norm(maxs - mins))
        self._bounds_diag = diag if diag > 0 else 10.0
