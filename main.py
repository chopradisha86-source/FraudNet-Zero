import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from gqlalchemy import Memgraph

from websocket_manager import manager
from topology_agent import detect_micro_layering_cycles, run_louvain_community_analysis
from risk_agent import analyze_and_score_accounts
from database import init_sqlite_db, verify_user_credentials
from auth import create_access_token, require_admin, get_current_user

app = FastAPI(
    title="FraudNet-Zero API Engine",
    description="Graph-Based Multi-Agent Engine for Real-Time Money Laundering Ring Detection & Asset Freezing",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to Memgraph container
memgraph = Memgraph(host="127.0.0.1", port=7687)

# --- Pydantic Data Models ---
class FreezeRequest(BaseModel):
    account_ids: list[str]
    reason: str = "Minimum-Cut Real-Time Isolation"

# --- Authentication Endpoint ---

@app.post("/api/v1/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticates analysts/admins against SQLite and returns a JWT access token."""
    user = verify_user_credentials(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "role": user["role"]
    }

# --- REST Endpoints ---

@app.get("/")
def read_root():
    return {"status": "ACTIVE", "system": "FraudNet-Zero Engine"}

@app.post("/api/v1/topology/louvain")
async def trigger_louvain_analysis(current_user: dict = Depends(get_current_user)):
    """Triggers Louvain community detection and dynamic threshold adjustment."""
    try:
        run_louvain_community_analysis()
        await manager.broadcast_event("TELEMETRY_LOG", {
            "agent": "Topology Agent",
            "message": "Executed Louvain Community Detection. Dynamic threshold (0.35) applied to high-risk clusters."
        })
        return {"status": "SUCCESS", "message": "Louvain community analysis complete."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/containment/execute")
async def execute_precision_isolation(
    request: FreezeRequest,
    current_user: dict = Depends(require_admin)  # 🔒 Protected: Requires ADMIN permissions
):
    """
    Automated Containment Agent: Freezes specified mule accounts in Memgraph 
    to break the laundering ring with zero collateral impact on clean nodes.
    """
    try:
        query = """
        UNWIND $accounts AS acc_id
        MATCH (a:Account {id: acc_id})
        SET a.status = 'FROZEN', a.risk_level = 'CONTAINED'
        RETURN a.id AS frozen_id;
        """
        results = list(memgraph.execute_and_fetch(query, parameters={"accounts": request.account_ids}))
        frozen_ids = [r["frozen_id"] for r in results]

        # Broadcast containment event to update the 3D Force Graph UI in real time
        await manager.broadcast_event("CONTAINMENT_EXECUTION", {
            "frozen_accounts": frozen_ids,
            "reason": request.reason
        })
        
        await manager.broadcast_event("TELEMETRY_LOG", {
            "agent": "Automated Containment Agent",
            "message": f"🛡️ Precision Isolation Executed by {current_user['username']}! Severed accounts: {', '.join(frozen_ids)}"
        })

        return {
            "status": "CONTAINED",
            "frozen_accounts": frozen_ids,
            "count": len(frozen_ids)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute containment: {str(e)}")

# --- Real-Time Telemetry Background Loop ---

async def telemetry_background_worker():
    """Periodically queries graph state and streams updates via WebSockets."""
    while True:
        try:
            # 1. Fetch active cycles
            cycles = detect_micro_layering_cycles()
            if cycles:
                await manager.broadcast_event("CYCLE_ALERT", {"cycles": cycles})

            # 2. Fetch top risk suspects with SHAP attributions
            risk_suspects = analyze_and_score_accounts()
            if risk_suspects:
                await manager.broadcast_event("RISK_SCORES", {"suspects": risk_suspects})

        except Exception as e:
            print(f"⚠️ Telemetry worker error: {e}")
            
        await asyncio.sleep(3)  # Push metrics every 3 seconds

@app.on_event("startup")
async def startup_event():
    # 1. Initialize SQLite database and seed default user roles
    init_sqlite_db()
    # 2. Start the async telemetry worker loop on API startup
    asyncio.create_task(telemetry_background_worker())

# --- WebSocket Channel ---

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive & receive client trigger messages
            data = await websocket.receive_text()
            print(f"📩 Message from UI client: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)