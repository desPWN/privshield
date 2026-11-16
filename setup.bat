@echo off
title PrivShield Setup
echo ==========================================
echo   PrivShield - Initial Setup
echo ==========================================
echo.

echo [1/2] Installing Python backend packages...
python -m pip install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python package installation failed. Make sure Python 3.10+ is installed and added to PATH.
    pause
    exit /b %errorlevel%
)

echo.
echo [2/2] Installing Frontend packages (npm)...
cd frontend
call npm install
cd ..
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] npm install failed. Make sure Node.js is installed.
    pause
    exit /b %errorlevel%
)

echo.
echo ==========================================
echo   Setup Complete!
echo   Double-click 'start.bat' to launch the app.
echo ==========================================
pause

