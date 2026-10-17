@echo off
echo ============================================================
echo   Building FOSSEverything Windows Installer...
echo ============================================================
uv run python scripts/build_installer.py
pause
