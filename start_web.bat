@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating local Python virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create .venv. Install Python 3.12+ and ensure python is on PATH.
        exit /b 1
    )
)

echo Installing or verifying dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed.
    exit /b 1
)

echo Starting AAT Gel ROI/Lane Review Tool at http://127.0.0.1:8000
".venv\Scripts\python.exe" -m uvicorn app:app --app-dir Web --host 127.0.0.1 --port 8000
