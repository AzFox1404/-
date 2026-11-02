@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -X utf8 "%~dp0workspace_preview.py"
    goto finish
)
if defined BUREAU_ID_PYTHON (
    "%BUREAU_ID_PYTHON%" -X utf8 "%~dp0workspace_preview.py"
    goto finish
)
set "bureau_runtime=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%bureau_runtime%" (
    "%bureau_runtime%" -X utf8 "%~dp0workspace_preview.py"
    goto finish
)
python -X utf8 "%~dp0workspace_preview.py"
:finish
if errorlevel 1 pause
