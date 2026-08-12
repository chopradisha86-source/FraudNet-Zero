from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from gqlalchemy import Memgraph
import json
import os
import glob
from typing import List

# 1. INITIALIZE FASTAPI APP
app = FastAPI(title="FraudNet Zero API Bridge")

# 2. ENABLE CORS (Required for Next.js to talk to FastAPI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. CONNECT TO MEMGRAPH DATABASE
memgraph = Memgraph(host="127.0.0.1", port=7687)

# 4. WEBSOCKET CONNECTION MANAGER
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
        
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"⚠️ Error broadcasting to client: {e}")
                self.disconnect(connection)

# Global Connection Manager Instance
manager = ConnectionManager()

# 5. WEBSOCKET ROUTE FOR NEXT.JS
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keeps connection alive and receives incoming messages from UI
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# 6. REST API ENDPOINTS FOR NEXT.JS DYNAMIC FETCHING
@app.get("/api/stats")
def get_stats():
    """Returns high-level graph transaction metrics."""
    try:
        tx_res = list(memgraph.execute_and_fetch("MATCH ()-[r:TRANSFERRED]->() RETURN count(r) AS total_tx"))
        mule_res = list(memgraph.execute_and_fetch("MATCH (a:Account) WHERE a.is_mule = true OR a.id STARTS WITH 'MULE_' RETURN count(a) AS total_mules"))
        return {
            "total_tx": tx_res[0]["total_tx"] if tx_res else 0,
            "total_mules": mule_res[0]["total_mules"] if mule_res else 0,
            "status": "ONLINE"
        }
    except Exception as e:
        return {"total_tx": 0, "total_mules": 0, "status": f"Error: {str(e)}"}

@app.get("/api/suspects")
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
    except Exception as e:
        return []

@app.get("/api/sar/{account_id}")
def get_sar_report(account_id: str):
    """Fetches saved Gemini SAR narrative report."""
    saved_sars = glob.glob(f"reports/SAR_{account_id}_*.md")
    if saved_sars:
        latest_report = max(saved_sars, key=os.path.getmtime)
        with open(latest_report, "r", encoding="utf-8") as f:
            return {"type": "markdown", "content": f.read()}
    return {"type": "none", "message": "No SAR report generated yet."}

@app.post("/api/containment/freeze/{account_id}")
async def freeze_account(account_id: str):
    """Triggers containment isolation and broadcasts WebSocket alert to Next.js UI."""
    try:
        query = "MATCH (a:Account {id: $account_id}) SET a.status = 'FROZEN' RETURN a.id AS id"
        memgraph.execute_and_fetch(query, parameters={"account_id": account_id})
        
        # Broadcast real-time containment event via WebSockets
        await manager.broadcast_event(
            "CONTAINMENT_EXECUTION", 
            {"account_id": account_id, "action": "FROZEN", "status": "ISOLATED"}
        )
        return {"status": "SUCCESS", "message": f"Account {account_id} contained."}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}