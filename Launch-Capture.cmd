@echo off
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" "%~dp0.venv\Scripts\pythonw.exe" -m receiver.gui
    exit /b
)
if exist "%~dp0..\..\work\venv\Scripts\pythonw.exe" (
    start "" "%~dp0..\..\work\venv\Scripts\pythonw.exe" -m receiver.gui
    exit /b
)
echo Python environment not found. Run:
echo python -m venv .venv
echo .venv\Scripts\python -m pip install -r requirements-gui.txt
pause
