@echo off
setlocal

echo =============================================
echo Starting Enterprise Observability Pipeline (Windows)
echo =============================================
echo.

set SCRIPT_DIR=%~dp0
set VENV_PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe
set VENV_STREAMLIT=%SCRIPT_DIR%.venv\Scripts\streamlit.exe

if not exist "%VENV_PYTHON%" (
    echo Error: Virtual environment python not found at %VENV_PYTHON%.
    echo Please create your virtual environment first using:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    exit /b 1
)

echo [Step 1/3] Loading and cleaning raw Excel data...
"%VENV_PYTHON%" "%SCRIPT_DIR%db_loader.py"
if %errorlevel% neq 0 (
    echo Error running db_loader.py!
    exit /b %errorlevel%
)
echo.

echo [Step 2/3] Running SQL analysis and generating visual dashboard...
"%VENV_PYTHON%" "%SCRIPT_DIR%analyzer.py"
if %errorlevel% neq 0 (
    echo Error running analyzer.py!
    exit /b %errorlevel%
)
echo.

echo [Step 3/3] Generating and dispatching executive email report...
"%VENV_PYTHON%" "%SCRIPT_DIR%send_report.py"
if %errorlevel% neq 0 (
    echo Error running send_report.py!
    exit /b %errorlevel%
)
echo.

echo =============================================
echo PIPELINE COMPLETE!
echo.
echo To launch the interactive local web dashboard portal, run:
echo   .venv\Scripts\streamlit.exe run app.py
echo =============================================
exit /b 0
