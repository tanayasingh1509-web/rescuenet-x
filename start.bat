@echo off
TITLE RESCUENET-X Tactical Command Center
echo ============================================================
echo   RESCUENET-X DISASTER INTELLIGENCE PLATFORM
echo   Omnichannel Emergency Response & Automated Dispatch
echo ============================================================
echo.
echo Starting FastAPI & WebSocket Server on http://localhost:8000...
echo.

start "RESCUENET-X Server" python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
timeout /t 3 /nobreak >nul

echo.
echo Opening Tactical Command Dashboard in your browser...
start http://localhost:8000/
echo.
echo ============================================================
echo   SYSTEM ONLINE:
echo   - Command Dashboard: http://localhost:8000/
echo   - Citizen SOS View:  http://localhost:8000/ (Click Citizen SOS)
echo   - Swagger API Docs:  http://localhost:8000/docs
echo   - Real-time Stream:  ws://localhost:8000/ws
echo ============================================================
echo.
pause
