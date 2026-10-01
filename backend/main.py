"""
Main FastAPI Application for RESCUENET-X
Omnichannel Disaster Intelligence & Automated Dispatch Platform
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .config import HOST, PORT, DEBUG, AUDIO_UPLOAD_DIR, IMAGE_UPLOAD_DIR
from .websocket_manager import ws_manager
from .routes import voice, report, simulate, dispatch
from .store import store
from .schemas import EventPayload, Coordinates

app = FastAPI(
    title="RESCUENET-X Engine",
    description="Omnichannel Crisis Intelligence & Zero-Latency Dispatch Platform",
    version="1.0.0"
)

# CORS middleware allowing local frontend dev server and PWA clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static asset routes for uploaded audio/images
app.mount("/uploads/images", StaticFiles(directory=str(IMAGE_UPLOAD_DIR)), name="images")
app.mount("/uploads/audio", StaticFiles(directory=str(AUDIO_UPLOAD_DIR)), name="audio")

# Include API Routers
from .routes import config
app.include_router(voice.router)
app.include_router(report.router)
app.include_router(simulate.router)
app.include_router(dispatch.router)
app.include_router(config.router)

# Mount Frontend static build if present
from pathlib import Path
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/dashboard", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="dashboard")
    # Also mount root for direct access if index.html is present
    from fastapi.responses import FileResponse
    @app.get("/")
    async def serve_index():
        return FileResponse(str(FRONTEND_DIST / "index.html"))
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

@app.websocket("/ws")
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    FR-3.1 Real-Time Streaming:
    WebSocket connection endpoint. Pushes Section 4.5 event payloads to the dashboard in < 50ms.
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
            # Keep-alive heartbeat & client command receiver
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

@app.on_event("startup")
async def startup_event():
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=DEBUG)
