@echo off
setlocal
cd /d "%~dp0"

set "VENV_PY=.venv\Scripts\python.exe"
set "PYTHON_CMD="

if exist "%VENV_PY%" goto :install_deps

call :find_python
if not defined PYTHON_CMD (
    echo Failed to find a usable Python interpreter.
    echo Install Python, or make sure the Python launcher or python.exe is available.
    exit /b 1
)

echo Creating virtual environment with %PYTHON_CMD%...
%PYTHON_CMD% -m venv .venv
if errorlevel 1 (
    echo Failed to create virtual environment.
    exit /b 1
)

:install_deps
if not exist "%VENV_PY%" (
    echo Virtual environment is missing or incomplete.
    exit /b 1
)

echo Installing/updating dependencies...
"%VENV_PY%" -m pip install --upgrade pip -q
if errorlevel 1 (
    echo Failed to upgrade pip.
    exit /b 1
)
"%VENV_PY%" -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo Failed to install dependencies.
    exit /b 1
)

echo Launching IMS Control...
"%VENV_PY%" main.py

endlocal
exit /b 0

:find_python
for %%C in (
    "py -3.11"
    "py -3"
    "python"
    "python3"
) do (
    call %%~C -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=%%~C"
        exit /b 0
    )
)

if exist "%LocalAppData%\Programs\Python\Python314\python.exe" (
    set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python314\python.exe"
    exit /b 0
)

if exist "%LocalAppData%\Programs\Python\Python313\python.exe" (
    set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python313\python.exe"
    exit /b 0
)

if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
    exit /b 0
)

if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python311\python.exe"
    exit /b 0
)

if exist "%LocalAppData%\Python\pythoncore-3.14-64\python.exe" (
    set "PYTHON_CMD=%LocalAppData%\Python\pythoncore-3.14-64\python.exe"
    exit /b 0
)

if exist "%LocalAppData%\Python\pythoncore-3.11-64\python.exe" (
    set "PYTHON_CMD=%LocalAppData%\Python\pythoncore-3.11-64\python.exe"
    exit /b 0
)

exit /b 0
