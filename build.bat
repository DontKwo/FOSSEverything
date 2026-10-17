@echo off
echo ============================================================
echo   Building FOSSEverything Standalone Executable...
echo ============================================================
uv run python scripts/build_executable.py %*
pause
