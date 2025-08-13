@echo off
:: Set up paths
SET SCRIPT_NAME=your_script.py
SET DIST_DIR=dist

:: Step 1: Install dependencies (ensure PyInstaller is installed)
pip install pyinstaller

:: Step 2: Package the Python script into a single executable file
pyinstaller --onefile --windowed %SCRIPT_NAME%

:: Step 3: Notify user of completion
echo Windows executable built successfully!
echo The executable is located in: %DIST_DIR%\your_script.exe
pause
