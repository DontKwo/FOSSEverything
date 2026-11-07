@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   FOSSEverything - Standalone Executable Builder
echo ============================================================
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

where uv >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [INFO] Running test suite...
    uv run python -m pytest -q
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] Tests failed. Aborting build.
        exit /b 1
    )
    echo [INFO] Using uv runner...
    uv run python scripts/build_executable.py %*
    goto finish
)

if exist ".venv\Scripts\python.exe" (
    echo [INFO] uv not found in PATH; using local .venv\Scripts\python.exe...
    ".venv\Scripts\python.exe" scripts/build_executable.py %*
    goto finish
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [INFO] uv not found; falling back to system python...
    python scripts/build_executable.py %*
    goto finish
)

echo [ERROR] No suitable Python interpreter found.
echo Please install uv (https://astral.sh/uv) or Python 3.11+.
exit /b 1

:finish
if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUCCESS] Build completed! Check the 'dist' directory.
) else (
    echo.
    echo [ERROR] Build failed with exit code %ERRORLEVEL%.
)
echo.
pause
