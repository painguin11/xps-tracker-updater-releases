@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title XPS Tracker Updater Setup

echo ======================================
echo       XPS Tracker Updater Setup
echo ======================================
echo.

set "PYEXE="
call :find_python

if not defined PYEXE (
    echo Python was not found.
    echo.
    where winget >nul 2>nul
    if errorlevel 1 (
        echo Automatic installation is not available because Windows Package Manager ^(winget^) was not found.
        echo.
        echo Please install Python 3.12 from python.org.
        echo IMPORTANT: Check "Add python.exe to PATH" during installation.
        echo Then run this file again.
        echo.
        pause
        exit /b 1
    )

    echo Installing Python 3.12. This may take a minute...
    winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo.
        echo Python installation did not complete successfully.
        echo Please install Python 3.12 manually from python.org and run this file again.
        pause
        exit /b 1
    )

    call :find_python
    if not defined PYEXE (
        echo.
        echo Python installed, but Windows has not refreshed PATH yet.
        echo Close this window, then double-click setup_and_run.bat again.
        pause
        exit /b 0
    )
)

echo Using Python: %PYEXE%
"%PYEXE%" --version

echo.
echo Checking the updater environment...
set "VPY=%CD%\.venv\Scripts\python.exe"
if exist "%VPY%" (
    "%VPY%" --version >nul 2>nul
    if errorlevel 1 (
        echo The existing environment belongs to another Python installation.
        echo Rebuilding it for this computer...
        rmdir /s /q ".venv"
    )
)
if not exist ".venv\Scripts\python.exe" (
    "%PYEXE%" -m venv .venv
    if errorlevel 1 goto :venvfail
)

set "VPY=%CD%\.venv\Scripts\python.exe"
"%VPY%" -c "import fitz, PIL, pytesseract, cv2, win32com.client" >nul 2>nul
if errorlevel 1 (
    echo Installing required packages. This is only needed on first setup or after a repair...
    "%VPY%" -m pip install --upgrade pip
    if errorlevel 1 goto :depfail
    "%VPY%" -m pip install pymupdf pillow pytesseract opencv-python pywin32
    if errorlevel 1 goto :depfail
) else (
    echo Required packages are already installed.
)

set "TESS="
call :find_tesseract
if not defined TESS (
    echo.
    echo Tesseract OCR was not found.
    where winget >nul 2>nul
    if not errorlevel 1 (
        echo Installing Tesseract OCR...
        winget install --id UB-Mannheim.TesseractOCR -e --accept-package-agreements --accept-source-agreements
    )
    call :find_tesseract
)

if not defined TESS (
    echo.
    echo WARNING: Tesseract OCR still was not found.
    echo The program can open, but PDF analysis will not work until Tesseract is installed.
    echo You can install it and then run this launcher again.
    echo.
    pause
) else (
    echo Using Tesseract: %TESS%
)

call :create_shortcut

echo.
echo Starting XPS Tracker Updater...
"%VPY%" xps_update.py
if errorlevel 20 exit /b 0
"%VPY%" reno_scan_updater.py
if errorlevel 1 (
    echo.
    echo The updater closed with an error. Copy or screenshot the message above and send it to me.
    pause
)
exit /b 0

:create_shortcut
echo Creating/updating desktop shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell;$d=$w.SpecialFolders('Desktop');$s=$w.CreateShortcut((Join-Path $d 'XPS Tracker Updater.lnk'));$s.TargetPath='%CD%\run_xps_tracker.bat';$s.WorkingDirectory='%CD%';$s.IconLocation='%CD%\xps_tracker_shortcut.ico,0';$s.Save()" >nul 2>nul
if errorlevel 1 echo WARNING: The desktop shortcut could not be created.
exit /b 0

:find_python
for %%P in (python.exe py.exe) do (
    if not defined PYEXE (
        for /f "delims=" %%I in ('where %%P 2^>nul') do (
            echo %%I | findstr /I "WindowsApps" >nul
            if errorlevel 1 set "PYEXE=%%I"
        )
    )
)
if not defined PYEXE (
    for %%D in (312 313 311) do (
        if exist "%LOCALAPPDATA%\Programs\Python\Python%%D\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python%%D\python.exe"
    )
)
if not defined PYEXE (
    for %%D in (312 313 311) do (
        if exist "C:\Program Files\Python%%D\python.exe" set "PYEXE=C:\Program Files\Python%%D\python.exe"
    )
)
exit /b 0

:find_tesseract
set "TESS="
for %%T in (
    "%ProgramFiles%\Tesseract-OCR\tesseract.exe"
    "%ProgramFiles(x86)%\Tesseract-OCR\tesseract.exe"
    "%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"
) do (
    if not defined TESS if exist "%%~T" set "TESS=%%~T"
)
if not defined TESS (
    for /f "delims=" %%I in ('where tesseract.exe 2^>nul') do (
        if not defined TESS set "TESS=%%I"
    )
)
exit /b 0

:venvfail
echo.
echo Could not create the Python environment.
echo Please send me a screenshot of the messages above.
pause
exit /b 1

:depfail
echo.
echo Dependency installation failed.
echo Please send me a screenshot of the messages above.
pause
exit /b 1
