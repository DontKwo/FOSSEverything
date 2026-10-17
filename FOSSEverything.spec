# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

# The optional CAD backend (cadquery-ocp) ships native binaries PyInstaller's
# static analysis can't discover on its own; collect it only if installed, so
# a base install without the `[cad]` extra still produces a working build.
ocp_datas, ocp_binaries, ocp_hidden = [], [], []
try:
    ocp_datas, ocp_binaries, ocp_hidden = collect_all('OCP')
except Exception:
    pass

# The 3D viewport is built on pyvista/VTK, both native-heavy with no
# registered PyInstaller hook entry points, so collect them explicitly.
pv_datas, pv_binaries, pv_hidden = collect_all('pyvista')
vtk_datas, vtk_binaries, vtk_hidden = collect_all('vtkmodules')
pvqt_datas, pvqt_binaries, pvqt_hidden = collect_all('pyvistaqt')

a = Analysis(
    ['C:/Users/Josh/projects/FOSSEverything/main.py'],
    pathex=[],
    binaries=[] + ocp_binaries + pv_binaries + vtk_binaries + pvqt_binaries,
    datas=[('C:/Users/Josh/projects/FOSSEverything/.venv/Lib/site-packages/imageio_ffmpeg/binaries', 'imageio_ffmpeg/binaries')] + ocp_datas + pv_datas + vtk_datas + pvqt_datas,
    hiddenimports=['PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.QtMultimedia', 'PyQt6.QtMultimediaWidgets', 'pymupdf', 'fitz', 'PIL', 'PIL.Image', 'imageio_ffmpeg', 'mutagen', 'tinytag', 'yaml', 'cv2', 'trimesh', 'shapely', 'mapbox_earcut'] + ocp_hidden + pv_hidden + vtk_hidden + pvqt_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# UPX shrinks the distributable but decompresses every native DLL/pyd at load
# time; with VTK/OpenCV/SciPy's large binary set, that tax outweighs the size win.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FOSSEverything',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='FOSSEverything',
)
