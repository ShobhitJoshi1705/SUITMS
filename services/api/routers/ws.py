import asyncio
import logging
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("suitms.api.ws")
router = APIRouter(tags=["WebSocket Real-Time Broadcast"])

class ConnectionManager:
    """Manages active WebSocket connections to broadcast live traffic and hazard alerts."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Remaining clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending to WebSocket client: {e}")
                self.disconnect(connection)

manager = ConnectionManager()

@router.websocket("/ws/live-feed")
async def websocket_live_feed(websocket: WebSocket):
    """
    Real-Time WebSocket stream pushing live violation detections, ALPR hits,
    and citizen hazard report submissions directly to the React dashboard.
    """
    await manager.connect(websocket)
    try:
        # Send initial handshake welcome
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "message": "Connected to SUITMS Real-Time Event Stream"
        })
        while True:
            # Keep socket alive and accept ping/pong or client subscription requests
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket handler exited: {e}")
        manager.disconnect(websocket)
