"""
Main FastAPI Application for RESCUENET-X
Omnichannel Disaster Intelligence & Automated Dispatch Platform (Phase 3 Architecture)
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from pathlib import Path
import os
import time
import json
import uuid
import logging
import traceback

from .config import HOST, PORT, DEBUG, AUDIO_UPLOAD_DIR, IMAGE_UPLOAD_DIR, ALLOWED_ORIGINS_LIST
from .websocket_manager import ws_manager
from .routes import voice, report, simulate, dispatch, config
from .store import store
from .schemas import EventPayload, Coordinates
from .database import get_db_connection

# Phase 3.4: Logging setup with levels and format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("rescuenet.app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern FastAPI lifespan context manager."""
    logger.info("=" * 60)
    logger.info("🚀 RESCUENET-X DISASTER INTELLIGENCE PLATFORM STARTED")
    logger.info(f"📡 Backend running on http://{HOST}:{PORT}")
    logger.info("⚡ Real-time WebSocket: /ws")
    logger.info("=" * 60)

    # Seed baseline incident if store is completely empty
    if not store.list_events():
        seed_event = EventPayload(
            category="FLOOD",
            coordinates=Coordinates(lat=28.6189, lng=77.2020),
            sector="Yamuna River Embankment B-3",
            severity=8,
            casualty_count=2,
            summary="Water level rising above danger mark. 2 civilians stranded near floodgate.",
            confidence=0.92,
            source="voice",
            raw_transcript="Water is rising rapidly near the old floodgate barrier. Two people stranded.",
            verified=True,
            status="DISPATCHED",
            assigned_unit={
                "id": "NDRF-ALPHA-1",
                "name": "NDRF Disaster Response Squad Alpha",
                "unit_type": "RESCUE",
                "distance_km": 1.2,
                "eta_minutes": 3,
                "contact": "+91-11-24363260"
            }
        )
        store.add_event(seed_event)

    yield

    logger.info("[SYSTEM] RESCUENET-X Engine gracefully shutting down.")

app = FastAPI(
    title="RESCUENET-X Engine",
    description="Omnichannel Crisis Intelligence & Zero-Latency Dispatch Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Exception handler for Pydantic schema validation errors (HTTP 422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        errors.append({"field": field, "message": msg, "type": err.get("type")})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Request validation failed", "errors": errors}
    )

# Global catch-all exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[REQ {req_id}] {request.method} {request.url.path}: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred", "message": str(exc), "request_id": req_id}
    )

# Phase 3.4: Request ID middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
    request.state.request_id = req_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response

# Phase 2.6: Security Headers Middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    if request.url.path.startswith("/uploads/"):
        lower = request.url.path.lower()
        if lower.endswith(".html") or lower.endswith(".htm") or lower.endswith(".svg"):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Execution of scriptable markup files (.html, .svg) from uploads is forbidden."}
            )

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: data: blob:; "
        "img-src 'self' https: data: blob:; "
        "connect-src 'self' https: wss: ws:;"
    )
    return response

# Phase 2.2: CORS middleware restricted to allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount static asset routes for uploaded audio/images
app.mount("/uploads/images", StaticFiles(directory=str(IMAGE_UPLOAD_DIR)), name="images")
app.mount("/uploads/audio", StaticFiles(directory=str(AUDIO_UPLOAD_DIR)), name="audio")

# Include API Routers
app.include_router(voice.router)
app.include_router(report.router)
app.include_router(simulate.router)
app.include_router(dispatch.router)
app.include_router(config.router)

@app.websocket("/ws")
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Phase 3.3 Real-Time Streaming:
    - Sequence numbered delivery
    - Server-side ping/pong carrying server timestamp for true latency measurement
    - Resync support via gap detection
    - Read-only; client commands ignored
    """
    await ws_manager.connect(websocket)
    try:
        events = store.list_events()
        units = store.list_units()
        await websocket.send_json({
            "type": "INITIAL_STATE",
            "seq": ws_manager.current_seq(),
            "server_time": time.time(),
            "events": [e.model_dump() for e in events],
            "units": [u.model_dump() for u in units]
        })

        while True:
            raw_text = await websocket.receive_text()
            now = time.time()

            # Handle simple string 'ping'
            if raw_text == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "server_time": now
                })
                continue

            # Handle structured JSON control messages
            try:
                msg = json.loads(raw_text)
                msg_type = msg.get("type", "")

                if msg_type == "ping":
                    client_time = msg.get("client_time")
                    await websocket.send_json({
                        "type": "pong",
                        "server_time": now,
                        "client_time": client_time
                    })
                elif msg_type == "RESYNC":
                    last_seq = int(msg.get("last_seq", 0))
                    missed = ws_manager.get_messages_since(last_seq)
                    if missed:
                        for m in missed:
                            await websocket.send_json(m)
                    else:
                        # Full snapshot resync
                        evs = store.list_events()
                        uns = store.list_units()
                        await websocket.send_json({
                            "type": "INITIAL_STATE",
                            "seq": ws_manager.current_seq(),
                            "server_time": now,
                            "events": [e.model_dump() for e in evs],
                            "units": [u.model_dump() for u in uns]
                        })
                # Client data-modification commands are strictly ignored (read-only)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
        await ws_manager.disconnect(websocket)

@app.get("/health")
async def health_check():
    """Phase 3.4 /health check reporting DB status, whisper/yolo, active WS count, total events."""
    db_status = "connected"
    try:
        conn = get_db_connection()
        conn.cursor().execute("SELECT 1")
        conn.close()
    except Exception as e:
        db_status = f"error: {e}"

    from .ai_engine import whisper
    from .vision_engine import yolo_model

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": "RESCUENET-X",
        "version": "1.0.0",
        "database": db_status,
        "whisper_available": bool(whisper is not None),
        "yolo_available": bool(yolo_model is not None),
        "active_ws_connections": len(ws_manager.active_connections),
        "total_events": len(store.list_events())
    }

# Mount Frontend static build after all API routes
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/dashboard", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="dashboard")
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=DEBUG)
