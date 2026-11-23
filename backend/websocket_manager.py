"""
WebSocket Connection Manager for RESCUENET-X
Handles live streaming of disaster events, cluster updates, and unit dispatch alerts.
"""

from typing import List, Dict, Any
from fastapi import WebSocket
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WS] Client connected. Total active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[WS] Client disconnected. Remaining: {len(self.active_connections)}")

    async def broadcast_event(self, event_data: Dict[str, Any]):
        """
        Broadcasts Section 4.5 structured event payload in real time to all connected dashboards.
        Target latency: < 50ms.
        """
        if not self.active_connections:
            return

        message = {
            "type": "INCIDENT_UPDATE",
            "payload": event_data
        }

        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"[WS] Broadcast error: {e}")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)

    async def broadcast_unit_update(self, unit_data: Dict[str, Any]):
        """Broadcasts unit status changes (e.g. AVAILABLE, EN_ROUTE, BUSY)."""
        if not self.active_connections:
            return

        message = {
            "type": "UNIT_UPDATE",
            "unit": unit_data
        }

        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"[WS] Unit update broadcast error: {e}")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)

    async def broadcast_dispatch_alert(self, event_id: str, unit_info: Dict[str, Any]):
        """Notifies dashboards of unit dispatch confirmation."""
        message = {
            "type": "DISPATCH_CONFIRMED",
            "event_id": event_id,
            "unit": unit_info
        }
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)

# Singleton manager
ws_manager = ConnectionManager()
