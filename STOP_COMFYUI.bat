@echo off
setlocal
cd /d "%~dp0"
call Scripts\environment.bat
"ComfyUI\.venv\Scripts\python.exe" Scripts\manage_comfyui.py stop
if errorlevel 1 pause
