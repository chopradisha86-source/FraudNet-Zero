"""
Real-time connection manager + REST endpoints that expose graph telemetry
to the Next.js frontend.

FIX (integration gap): this file previously instantiated its own
`FastAPI()` app, its own Memgraph connection, and its own `/ws`,
`/api/stats`, `/api/suspects`, `/api/sar/{id}` and freeze routes.
Because only `main.py`'s app is ever passed to uvicorn, none of those
routes were reachable — the frontend would 404 on all of them.

This version exposes:
  - `manager`: a single ConnectionManager instance, imported by main.py
  - `router`: an APIRouter with the REST endpoints, included by main.py

so there is exactly one FastAPI app and one Memgraph connection for the
whole backend.
"""
import glob
import json
import os
from typing import List

from fastapi import APIRouter, WebSocket
from gqlalchemy import Memgraph

memgraph = Memgraph(host="127.0.0.1", port=7687)

router = APIRouter()


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
        - 'TELEMETRY_LOG'          (Terminal messages)
        - 'GRAPH_UPDATE'           (Node/Edge status changes, cut-edges to highlight red)
        - 'RISK_SCORES'            (Top suspect table with SHAP attributions)
        - 'CYCLE_ALERT'            (Detected laundering cycles)
        - 'CONTAINMENT_EXECUTION'  (Accounts frozen)
        """
        message = json.dumps({"event": event_type, "data": payload})

        # Iterate over a copy: disconnect() mutates active_connections mid-loop
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"⚠️ Error broadcasting to client: {e}")
                self.disconnect(connection)


# Global Connection Manager Instance — imported by main.py
manager = ConnectionManager()


# ---------------------------------------------------------------------------
# REST endpoints (now correctly mounted via main.py's app.include_router)
# ---------------------------------------------------------------------------

@router.get("/api/stats")
def get_stats():
    """Returns high-level graph transaction metrics."""
    try:
        tx_res = list(memgraph.execute_and_fetch("MATCH ()-[r:TRANSFERRED]->() RETURN count(r) AS total_tx"))
        mule_res = list(memgraph.execute_and_fetch(
            "MATCH (a:Account) WHERE a.is_mule = true OR a.id STARTS WITH 'MULE_' RETURN count(a) AS total_mules"
        ))
        return {
            "total_tx": tx_res[0]["total_tx"] if tx_res else 0,
            "total_mules": mule_res[0]["total_mules"] if mule_res else 0,
            "status": "ONLINE",
        }
    except Exception as e:
        return {"total_tx": 0, "total_mules": 0, "status": f"Error: {str(e)}"}


@router.get("/api/suspects")
def get_suspects():
    """Fetches high-risk accounts."""
    query = """
    MATCH (a:Account)
    WHERE a.is_mule = true OR a.id STARTS WITH 'MULE_'
    RETURN a.id AS account_id, coalesce(a.risk_score, 0.95) AS risk_score
    LIMIT 10
    """
    try:
        return list(memgraph.execute_and_fetch(query))
    except Exception:
        return []


@router.get("/api/sar/{account_id}")
def get_sar_report(account_id: str):
    """Fetches saved Gemini SAR narrative report from disk."""
    saved_sars = glob.glob(f"reports/SAR_{account_id}_*.md")
    if saved_sars:
        latest_report = max(saved_sars, key=os.path.getmtime)
        with open(latest_report, "r", encoding="utf-8") as f:
            return {"type": "markdown", "content": f.read()}
    return {"type": "none", "message": "No SAR report generated yet."}