"""
Main FastAPI Application for RESCUENET-X
Omnichannel Disaster Intelligence & Automated Dispatch Platform
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from pathlib import Path
import os
import traceback

from .config import HOST, PORT, DEBUG, AUDIO_UPLOAD_DIR, IMAGE_UPLOAD_DIR, ALLOWED_ORIGINS_LIST
from .websocket_manager import ws_manager
from .routes import voice, report, simulate, dispatch, config
from .store import store
from .schemas import EventPayload, Coordinates

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern FastAPI lifespan context manager replacing deprecated startup/shutdown events."""
    print("=" * 60)
    print("🚀 RESCUENET-X DISASTER INTELLIGENCE PLATFORM STARTED")
    print(f"📡 Backend running on http://{HOST}:{PORT}")
    print("⚡ Real-time WebSocket: /ws")
    print("=" * 60)

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

    # Lifespan teardown
    print("[SYSTEM] RESCUENET-X Engine gracefully shutting down.")

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

# Global catch-all exception handler to return clean JSON error instead of 500 crash
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[UNHANDLED EXCEPTION] {request.method} {request.url.path}: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred", "message": str(exc)}
    )

# Phase 2.6: Security Headers Middleware (CSP, X-Content-Type-Options, Referrer-Policy, Uploads execution protection)
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    # Prevent HTML or SVG execution from uploaded asset folders
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

# Phase 2.2: CORS middleware restricted to allowed origins (no wildcard with credentials)
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
    FR-3.1 Real-Time Streaming:
    WebSocket connection endpoint. Pushes Section 4.5 event payloads to the dashboard in < 50ms.
    Strictly read-only; ignores any client modification commands.
    """
    await ws_manager.connect(websocket)
    try:
        # Send current snapshot upon connection
        events = store.list_events()
        units = store.list_units()
        await websocket.send_json({
            "type": "INITIAL_STATE",
            "events": [e.model_dump() for e in events],
            "units": [u.model_dump() for u in units]
        })

        while True:
            # Keep-alive heartbeat receiver (strictly read-only; ignores client commands)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"[WS] Connection error: {e}")
        ws_manager.disconnect(websocket)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "RESCUENET-X",
        "version": "1.0.0",
        "connections": len(ws_manager.active_connections),
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
