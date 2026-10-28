import os
import sys
from PyInstaller.utils.hooks import collect_all

ROOT_DIR = SPECPATH

# Collect ffmpeg binaries dynamically
ffmpeg_datas = []
try:
    import imageio_ffmpeg
    ffmpeg_bin_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
    if os.path.exists(ffmpeg_bin_dir):
        ffmpeg_datas.append((ffmpeg_bin_dir, 'imageio_ffmpeg/binaries'))
except Exception:
    pass

assets_dir = os.path.join(ROOT_DIR, 'assets')
assets_datas = [(assets_dir, 'assets')] if os.path.exists(assets_dir) else []
web_dir = os.path.join(ROOT_DIR, 'app', 'web')
web_datas = [(web_dir, 'app/web')] if os.path.exists(web_dir) else []

# Collect pywebview interop libraries for frozen mode
import webview
webview_lib_dir = os.path.join(os.path.dirname(webview.__file__), 'lib')
webview_datas = []
if os.path.exists(webview_lib_dir):
    webview_datas.append((webview_lib_dir, 'webview/lib'))
    webview_datas.append((webview_lib_dir, '.'))

# Collect language_tool_python package data (integrity.toml etc)
lt_datas, lt_binaries, lt_hidden = [], [], []
try:
    lt_datas, lt_binaries, lt_hidden = collect_all('language_tool_python')
except Exception:
    pass

# The optional CAD backend (cadquery-ocp) ships native binaries PyInstaller's
# static analysis can't discover on its own; collect it only if installed, so
# a base install without the `[cad]` extra still produces a working build.
ocp_datas, ocp_binaries, ocp_hidden = [], [], []
try:
    ocp_datas, ocp_binaries, ocp_hidden = collect_all('OCP')
except Exception:
    pass

a = Analysis(
    [os.path.join(ROOT_DIR, 'main.py')],
    pathex=[ROOT_DIR],
    binaries=[] + ocp_binaries + lt_binaries,
    datas=assets_datas + web_datas + ffmpeg_datas + ocp_datas + lt_datas + webview_datas,
    hiddenimports=['webview', 'pythonnet', 'clr_loader', 'bottle', 'proxy_tools', 'pymupdf', 'fitz', 'PIL', 'PIL.Image', 'imageio_ffmpeg', 'mutagen', 'tinytag', 'yaml', 'cv2', 'trimesh', 'shapely', 'mapbox_earcut'] + ocp_hidden + lt_hidden,
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
    icon=os.path.join(assets_dir, 'icon.ico') if os.path.exists(os.path.join(assets_dir, 'icon.ico')) else None,
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
