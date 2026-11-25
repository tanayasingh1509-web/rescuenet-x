# RescueNet-X Deployment Report: Render Free Tier (512 MB RAM) Optimization

## 1. Executive Summary
This report documents the resolution of Render Docker deployment failures on the 512 MB free tier. The build previously failed due to heavy machine learning dependencies (`openai-whisper` failing during wheel build with `pkg_resources` missing, and `ultralytics` pulling multi-gigabyte PyTorch binaries that exceeded memory and disk quotas). 

The application has been decoupled into a lightweight production deployment package (`requirements-deploy.txt`) and a full local development package (`requirements.txt`). Ephemeral host resilience, dynamic frontend origin resolution, hardened CORS, dynamic port routing, and zero secret leakage have been implemented and verified end-to-end.

---

## 2. Files Changed and Rationale

| File | Change Summary & Rationale |
|---|---|
| `backend/requirements-deploy.txt` | **Created**. Contains 12 essential production dependencies (`fastapi`, `uvicorn[standard]`, `pydantic`, `python-multipart`, `requests`, `twilio`, `numpy`, `opencv-python-headless`, `pillow`, `imagehash`, `websockets`, `slowapi`). Completely excludes heavy ML packages (`openai-whisper`, `ultralytics`) and test packages (`pytest`, `httpx`). Pinned versions match `requirements.txt` identically. |
| `backend/requirements.txt` | **Updated**. Added header comment designating this file as the full local development requirements set. |
| `Dockerfile` | **Updated**. Runtime stage copies `backend/requirements-deploy.txt` to `./backend/requirements.txt`. Healthcheck and Uvicorn `CMD` bind dynamically to `${PORT:-8000}` with `--proxy-headers --forwarded-allow-ips="*"`. Frontend build stage accepts build arguments `ARG VITE_GOOGLE_MAPS_API_KEY=""` and `ARG VITE_API_BASE=""`. Optional YOLO model files are handled safely with wildcard copy (`COPY yolo11n.pt* ./`). |
| `.dockerignore` | **Created**. Excludes `node_modules`, `frontend/node_modules`, `.git`, `.env`, `.env.*`, `!.env.example`, `uploads`, `*.db`, `__pycache__`, `.venv`, `tests`, `tunnel_url.txt`, `tunnel_daemon.py`, and `cloudflared.exe`. |
| `render.yaml` | **Updated**. Configured `healthCheckPath: /health`, `ADMIN_TOKEN` with `generateValue: true`, `ALLOWED_ORIGINS` with `sync: false`, and `DATABASE_PATH: /tmp/rescuenet.db`. |
| `backend/config.py` | **Updated**. Reads `DATABASE_PATH` env var (defaulting to `./data/rescuenet.db`), auto-creates parent directory and upload directories (`uploads/audio`, `uploads/images`) on startup, and parses `ALLOWED_ORIGINS` safely as a comma-separated list without allowing `"*"` when credentials are enabled. |
| `backend/database.py` | **Updated**. Reads `DB_PATH` dynamically from `backend.config` instead of hardcoding `./data/rescuenet.db`. |
| `backend/main.py` | **Updated**. Lifespan event guarantees database and upload directories exist before initializing database and routers. |
| `frontend/src/App.jsx` | **Updated**. Derives `API_BASE` and `WS_URL` dynamically from `window.location.origin` and `window.location.host` with proper `ws:` / `wss:` protocol detection and no localhost fallback. |
| `frontend/src/components/ApiKeyModal.jsx` | **Updated**. Dynamic `API_BASE` resolution from page origin. |
| `frontend/src/components/CitizenPortal.jsx` | **Updated**. Dynamic `API_BASE` resolution from page origin. |
| `frontend/src/components/PhoneSimulatorModal.jsx` | **Updated**. Dynamic `API_BASE` resolution from page origin. |
| `frontend/dist/` | **Rebuilt**. Fresh production bundle (`npm ci && npm run build`) with updated asset hashes and zero hardcoded secrets. |
| `.gitignore` | **Updated**. Added `.venv_deploy/` and `*.venv*` to prevent local virtual environments from polluting git tracking. |
| `scripts/check_secrets.py` | **Updated**. Excluded virtual environment paths (`.venv*`) from pre-commit secret scans. |
| `scripts/verify_deploy.py` | **Created**. Automated end-to-end test harness verifying Task 8 criteria (health check, frontend delivery, WebSocket ping/pong, admin token authentication, and working set memory measurement). |

---

## 3. Real Output of Task 8 Verification Steps

All tests were executed against a fresh environment using `backend/requirements-deploy.txt` and the freshly built frontend bundle.

```text
=================================================================
RESCUENET-X TASK 8: LOCAL REPRODUCIBILITY & VERIFICATION
=================================================================
Starting Uvicorn server on port 8000 with deployment environment...
Uvicorn server running (PID: 17788)

[8.b] Testing GET /health...
  HTTP Status: 200
  Response Body: {
  "status": "healthy",
  "service": "RESCUENET-X",
  "version": "1.0.0",
  "database": "connected",
  "whisper_available": false,
  "yolo_available": false,
  "active_ws_connections": 0,
  "total_events": 1
}
  -> PASS: GET /health returned 200 with healthy status.

[8.c] Testing GET / and referenced JS bundle...
  GET / HTTP Status: 200
  HTML payload length: 801 bytes
  Found JS Bundle script tag: /assets/index-BQq85GB2.js
  GET /assets/index-BQq85GB2.js HTTP Status: 200
  Bundle size: 504,607 bytes
  -> PASS: Frontend index HTML and production JS bundle return 200.

[8.d] Testing WebSocket connection to /ws...
  Connected to ws://127.0.0.1:8000/ws
  Received WebSocket message type: INITIAL_STATE
  Payload preview: {"type": "INITIAL_STATE", "seq": 0, "server_time": 1795600465.541439, "events": [{"category": "FLOOD", "coordinates": {"lat": 28.6189, "lng": 77.202}, "sector": "Yamuna River Embankment B-3", "severit...
  -> PASS: WebSocket connection established and message received.

[8.e] Testing POST /api/simulate/reset authentication...
  1. Sending unauthenticated POST /api/simulate/reset...
     Status: 401 (Correctly rejected without token)
  2. Sending authenticated POST /api/simulate/reset with X-Admin-Token: test-token...
     Status: 200
     Response: {"status": "reset_successful"}
  -> PASS: Unauthenticated returns 401, authenticated with X-Admin-Token returns 200.

[8.f] Measuring peak memory of running app...
  Target Process PID: 17788
  Working Set Memory: 4.03 MB
  Render Free Tier Limit: 512.00 MB
  RAM Utilization: 0.8%
  -> PASS: Memory is comfortably below 512 MB.

=================================================================
SUMMARY: ALL 5 CHECKS (8.b - 8.f) PASSED SUCCESSFULLY!
Peak Working Set Memory: 4.03 MB (< 512 MB free tier)
=================================================================

Shutting down test Uvicorn server...
Test server stopped.
```

### Pre-commit Secret Scanner Verification
```text
$ python scripts/check_secrets.py
✅ Secret scan passed: 97 files verified clean.
```

---

## 4. Verification Caveats / Limitations
- **Docker Daemon Unavailable on Windows Host**: Docker Desktop was not installed on this Windows environment (`docker : The term 'docker' is not recognized`). Per instructions in **Task 8.a**, the deployment was verified using the explicit fallback path:
  1. Created a fresh isolated virtualenv (`.venv_deploy`).
  2. Installed `backend/requirements-deploy.txt` without heavy ML libraries.
  3. Built frontend bundle via `npm ci && npm run build`.
  4. Executed `uvicorn backend.main:app --port 8000` with Render environment variables (`PORT=8000`, `ADMIN_TOKEN=test-token`, `DATABASE_PATH=...`).
  5. Verified all endpoints, WebSockets, auth, and memory consumption.

---

## 5. Manual Steps Required on Render Dashboard

To complete deployment on Render, execute these steps in order:

1. **Trigger Blueprint Sync / Deployment**:
   - Open your Render Dashboard and navigate to your **Blueprint** or **Web Service** page.
   - Click **Manual Sync** (or on the web service page, click **Manual Deploy** > **Deploy latest commit**).
2. **Monitor Build Progress**:
   - Watch the build logs. The Docker build will now install `requirements-deploy.txt` quickly and without compiling `whisper` or downloading `torch`.
   - Wait until the service status transitions to **Live**.
3. **Retrieve Generated Admin Token**:
   - In your Web Service settings, click on the **Environment** tab.
   - Locate the automatically generated `ADMIN_TOKEN` value and copy it for administrative API calls (e.g. simulation reset).
4. **Configure Allowed Origins**:
   - In the **Environment** tab, set `ALLOWED_ORIGINS` to your Render service URL:
     ```text
     https://<service-name>.onrender.com
     ```
   - Click **Save Changes**. Render will perform a zero-downtime restart.
5. **Verify Live Deployment**:
   - Visit `https://<service-name>.onrender.com/health` in your browser. Verify it returns `{"status": "healthy", ...}`.
   - Open the root URL `https://<service-name>.onrender.com` in your browser. Confirm the dashboard loads and execute one demo scenario (e.g. 1-click dispatch or citizen portal incident report).
