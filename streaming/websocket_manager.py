from fastapi import WebSocket
import json
from typing import List

class ConnectionManager:
    """Manages active WebSocket connections to stream telemetry logs and graph updates."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"📡 [WebSocket] Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"🔌 [WebSocket] Client disconnected. Remaining: {len(self.active_connections)}")

    async def broadcast_event(self, event_type: str, payload: dict):
        """
        Broadcasts structured events to all connected UI clients.
        
        event_type options: 
        - 'TELEMETRY_LOG' (Terminal messages)
        - 'GRAPH_UPDATE' (Node/Edge status changes)
        - 'RISK_SCORES' (Top suspect table with SHAP attributions)
        - 'CONTAINMENT_EXECUTION' (Minimum-cut isolation alerts)
        """
        message = json.dumps({
            "event": event_type,
            "data": payload
        })
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"⚠️ Error broadcasting to client: {e}")

# Global Connection Manager Instance
manager = ConnectionManager()