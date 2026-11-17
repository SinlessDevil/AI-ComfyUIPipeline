@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install.ps1" -Install -DownloadModels -Profile ui
if errorlevel 1 (
  echo Installation failed. Read the error above.
  pause
  exit /b 1
)
echo Installation finished. Open ComfyUI.lnk in this folder.
pause
