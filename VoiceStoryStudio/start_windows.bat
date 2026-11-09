@echo off
setlocal
cd /d "%~dp0"
where git >nul 2>nul || (echo Please install Git and add it to PATH. & pause & exit /b 1)
where ffmpeg >nul 2>nul || (echo Please install FFmpeg and add it to PATH. & pause & exit /b 1)
where ffprobe >nul 2>nul || (echo Please install FFprobe and add it to PATH. & pause & exit /b 1)
if not exist .venv (
  py -3.11 -m venv .venv || (echo Python 3.11 is required. & pause & exit /b 1)
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt || (echo Dependency install failed. & pause & exit /b 1)
python studio.py --ui
pause