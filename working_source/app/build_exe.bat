@echo off
setlocal
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller pymupdf pillow pytesseract opencv-python pywin32
pyinstaller --noconfirm --clean --onefile --windowed --name "XPS Tracker Updater" --icon "xps_tracker_updater.ico" --add-data "xps_tracker_updater.ico;." --add-data "xps_tracker_shortcut.ico;." reno_scan_updater.py
echo.
echo If the build succeeded, the EXE is in the dist folder.
pause
