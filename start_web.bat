@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "MIN_PYTHON=3.11"
set "PYTHON_CMD="

call :try_python "py -3.12"
if not defined PYTHON_CMD call :try_python "py -3.11"
if not defined PYTHON_CMD call :try_python "python"
if not defined PYTHON_CMD call :try_python "python3"
if not defined PYTHON_CMD if exist "..\.venv\Scripts\python.exe" call :try_python "..\.venv\Scripts\python.exe"

if not exist ".venv\Scripts\python.exe" (
    echo Creating local Python virtual environment...
    if not defined PYTHON_CMD (
        echo Failed to find Python %MIN_PYTHON% or newer.
        echo Install Python 3.12 from https://www.python.org/downloads/ and rerun this script.
        exit /b 1
    )
    echo Using %PYTHON_CMD%
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo Failed to create .venv. Install Python 3.12+ and ensure it is available through the Python Launcher or PATH.
        exit /b 1
    )
)

".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if errorlevel 1 (
    echo Existing .venv does not use Python %MIN_PYTHON% or newer, or it is broken.
    echo Delete the .venv folder, install Python 3.12, and rerun start_web.bat.
    exit /b 1
)

echo Installing or verifying dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed.
    exit /b 1
)

echo Starting AAT Gel ROI/Lane Review Tool at http://127.0.0.1:8000
".venv\Scripts\python.exe" -m uvicorn app:app --app-dir Web --host 127.0.0.1 --port 8000

goto :eof

:try_python
%~1 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=%~1"
exit /b 0
