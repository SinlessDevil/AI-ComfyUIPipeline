@echo off
setlocal
cd /d "%~dp0"
call Scripts\environment.bat
if not exist "ComfyUI\.venv\Scripts\python.exe" (
  echo Missing local Python environment. See Docs\README_SETUP.md.
  pause
  exit /b 1
)
call ComfyUI\.venv\Scripts\activate.bat
python Scripts\manage_comfyui.py start
set "COMFY_EXIT=%ERRORLEVEL%"
if not "%COMFY_EXIT%"=="0" pause
exit /b %COMFY_EXIT%
