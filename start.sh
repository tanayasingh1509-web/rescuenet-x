#!/usr/bin/env bash
set -e

echo "============================================================"
echo "  RESCUENET-X DISASTER INTELLIGENCE PLATFORM"
echo "  Omnichannel Emergency Response & Automated Dispatch"
echo "============================================================"
echo ""

echo "[1/3] Installing Python backend dependencies..."
python3 -m pip install -r backend/requirements.txt || {
    echo "[WARNING] pip install encountered warnings. Continuing..."
}

echo ""
echo "[2/3] Installing frontend dependencies & building bundle..."
(
    cd frontend
    npm install
    npm run build
)

echo ""
echo "[3/3] Starting RESCUENET-X Server on http://0.0.0.0:8000..."
echo "System ready: http://localhost:8000"
exec python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
