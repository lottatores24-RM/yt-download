@echo off
REM ---------------------------------------------------------------
REM  YouTube Downloader - launcher
REM  Double-click this file to start the app on Windows.
REM ---------------------------------------------------------------
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [setup] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Could not create venv. Is Python installed and on PATH?
        pause
        exit /b 1
    )
    echo [setup] Installing dependencies...
    call "venv\Scripts\python.exe" -m pip install --upgrade pip
    call "venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo [run] Starting YouTube Downloader...
call "venv\Scripts\python.exe" main.py

if errorlevel 1 pause
endlocal
