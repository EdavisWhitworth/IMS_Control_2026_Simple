@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment. Ensure Python is installed and on PATH.
        exit /b 1
    )
)

echo Installing/updating dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip -q
".venv\Scripts\python.exe" -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo Failed to install dependencies.
    exit /b 1
)

echo Launching IMS Control...
".venv\Scripts\python.exe" main.py

endlocal
