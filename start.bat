@echo off
title PrivShield Launcher
echo ==========================================
echo   PrivShield - Starting Application...
echo ==========================================
echo.

echo Starting FastAPI Backend on port 8000...
start "PrivShield Backend" cmd /k "python run_backend.py"

echo Starting Vite React Frontend on port 5173...
start "PrivShield Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ==========================================
echo   Servers are running!
echo   Open in browser: http://localhost:5173
echo ==========================================
echo.
timeout /t 3 >nul
start http://localhost:5173
pause

