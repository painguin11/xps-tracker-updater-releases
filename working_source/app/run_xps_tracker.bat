@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title XPS Tracker Updater

set "VPY=%CD%\.venv\Scripts\python.exe"
if not exist "%VPY%" goto :setup
"%VPY%" -c "import fitz, PIL, pytesseract, cv2, win32com.client" >nul 2>nul
if errorlevel 1 goto :setup

"%VPY%" xps_update.py
if errorlevel 20 exit /b 0

"%VPY%" reno_scan_updater.py
if errorlevel 1 (
    echo.
    echo The updater closed with an error. Copy or screenshot the message above and send it to me.
    pause
)
exit /b 0

:setup
call setup_and_run.bat
exit /b %errorlevel%
