@echo off
TITLE RESCUENET-X Tactical Command Center
echo ============================================================
echo   RESCUENET-X DISASTER INTELLIGENCE PLATFORM
echo   Omnichannel Emergency Response & Automated Dispatch
echo ============================================================
echo.

echo [1/3] Installing / verifying Python backend dependencies...
python -m pip install -r backend\requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Some dependencies failed to install. Continuing with installed environment...
)

echo.
echo [2/3] Building frontend production bundle...
cd frontend
call npm install
call npm run build
cd ..

echo.
echo [3/3] Starting FastAPI & WebSocket Server on http://localhost:8000...
echo.

start "RESCUENET-X Server" python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
timeout /t 3 /nobreak >nul

echo Opening Command Dashboard in your browser...
start http://localhost:8000/
echo.
echo ============================================================
echo   SYSTEM ONLINE:
echo   - Command Dashboard: http://localhost:8000/
echo   - Citizen SOS View:  http://localhost:8000/#/citizen
echo   - Swagger API Docs:  http://localhost:8000/docs
echo   - Real-time Stream:  ws://localhost:8000/ws
echo ============================================================
echo.
pause
