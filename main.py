"""
DIFF FROM ORIGINAL main.py — fixes applied:

1. `from agents.risk_agent import analyze_and_score_accounts` was importing
   a function that doesn't exist (it's a method on RealTimeRiskAgent).
   -> Now imports the class and instantiates a module-level singleton.

2. `streaming/websocket_manager.py`'s REST endpoints (/api/stats,
   /api/suspects, /api/sar/{id}) were defined on a second, never-run
   FastAPI app. -> Now imported as `router` and mounted with
   app.include_router().

3. CORS used allow_origins=["*"] with allow_credentials=True, which
   browsers reject. -> Now reads explicit origins from env (defaults to
   the Next.js dev server).

4. Frontend spec calls for `ws://localhost:8000/ws`; only `/ws/telemetry`
   existed. -> Both routes now exist and share one handler.

5. Min-cut containment logic existed in containment_agent.py but was
   never wired to an endpoint. -> New POST /api/v1/containment/analyze
   runs it and broadcasts a GRAPH_UPDATE event so the frontend can
   highlight cut-edges in red before anything is frozen.

6. Added a catch-all exception handler so unhandled errors return JSON
   instead of a bare 500 with no CORS headers (which the browser would
   report as a CORS failure, masking the real error).
"""
import os
import asyncio
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from gqlalchemy import Memgraph

from google import genai
from google.genai import errors

from streaming.websocket_manager import manager, router as telemetry_router
from gcn_core.topology_agent import detect_micro_layering_cycles, run_louvain_community_analysis
from agents.risk_agent import RealTimeRiskAgent
from containment_agent import run_containment_pipeline

from database import init_sqlite_db, verify_user_credentials
from auth import create_access_token, require_admin, get_current_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(
    title="FraudNet-Zero API Engine",
    description="Graph-Based Multi-Agent Engine for Real-Time Money Laundering Ring Detection & Asset Freezing",
    version="1.0.0",
)

# --- CORS ---
# FIX: allow_origins=["*"] + allow_credentials=True is invalid per the CORS
# spec and browsers will silently block it. Set explicit origin(s) via
# FRONTEND_ORIGINS env var (comma-separated), defaulting to the Next.js dev server.
_frontend_origins = os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FIX: mount the REST endpoints that were previously stranded on a
# never-run second FastAPI app in websocket_manager.py.
app.include_router(telemetry_router)

memgraph = Memgraph(host="127.0.0.1", port=7687)

# FIX: risk_agent.py exposes a class, not a module-level function.
# Instantiate once and reuse — this also avoids reloading the XGBoost
# model / SHAP explainer on every request.
risk_agent = RealTimeRiskAgent()


def get_genai_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY environment variable is missing or empty.")
    return genai.Client(api_key=api_key)


# --- Global error handler ---
# FIX: an unhandled exception previously returned a bare 500 without CORS
# headers, which browsers report as a CORS error — hiding the real cause.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"status": "ERROR", "detail": str(exc)},
    )


# --- Pydantic Data Models ---
class FreezeRequest(BaseModel):
    account_ids: list[str]
    reason: str = "Minimum-Cut Real-Time Isolation"


class SARRequest(BaseModel):
    account_id: str
    risk_score: float
    shap_drivers: list[str]
    detected_topology: str = "Multi-Node Directed Cycle"


class ContainmentAnalyzeRequest(BaseModel):
    target_account_id: str
    sink_account_id: str
    hops: int = 2


# --- Authentication ---

@app.post("/api/v1/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticates analysts/admins against SQLite and returns a JWT access token."""
    user = verify_user_credentials(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}


# --- REST Endpoints ---

@app.get("/")
def read_root():
    return {"status": "ACTIVE", "system": "FraudNet-Zero Engine"}


@app.post("/api/v1/topology/louvain")
async def trigger_louvain_analysis(current_user: dict = Depends(get_current_user)):
    """Triggers Louvain community detection and dynamic threshold adjustment."""
    run_louvain_community_analysis()
    await manager.broadcast_event("TELEMETRY_LOG", {
        "agent": "Topology Agent",
        "message": "Executed Louvain Community Detection. Dynamic threshold (0.35) applied to high-risk clusters.",
    })
    return {"status": "SUCCESS", "message": "Louvain community analysis complete."}


@app.post("/api/v1/containment/analyze")
async def analyze_containment(
    request: ContainmentAnalyzeRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    NEW ENDPOINT — this was the missing link between containment_agent.py's
    min-cut math and the API layer.

    Pulls a live subgraph around `target_account_id`, computes the minimum
    cut needed to zero out flow to `sink_account_id`, and broadcasts the
    cut-edges as a GRAPH_UPDATE event so the frontend can render them in
    red on the Cytoscape canvas *before* anything is actually frozen.
    """
    result = run_containment_pipeline(
        target_account_id=request.target_account_id,
        sink_account_id=request.sink_account_id,
        hops=request.hops,
    )

    if result.get("error"):
        raise HTTPException(status_code=422, detail=result["error"])

    await manager.broadcast_event("GRAPH_UPDATE", {
        "cut_edges": result["edges_to_sever"],
        "nodes_to_freeze": result["nodes_to_freeze"],
    })
    await manager.broadcast_event("TELEMETRY_LOG", {
        "agent": "Containment Agent",
        "message": (
            f"🔍 Min-cut computed by {current_user['username']}: "
            f"{len(result['edges_to_sever'])} edge(s), cut value {result['cut_value']:.2f}"
        ),
    })

    return result


@app.post("/api/v1/containment/execute")
async def execute_precision_isolation(
    request: FreezeRequest,
    current_user: dict = Depends(require_admin),  # 🔒 Protected: Requires ADMIN permissions
):
    """
    Freezes the specified mule accounts in Memgraph. Typically called after
    /api/v1/containment/analyze has identified which nodes to freeze.
    """
    query = """
    UNWIND $accounts AS acc_id
    MATCH (a:Account {id: acc_id})
    SET a.status = 'FROZEN', a.risk_level = 'CONTAINED'
    RETURN a.id AS frozen_id;
    """
    results = list(memgraph.execute_and_fetch(query, parameters={"accounts": request.account_ids}))
    frozen_ids = [r["frozen_id"] for r in results]

    await manager.broadcast_event("CONTAINMENT_EXECUTION", {
        "frozen_accounts": frozen_ids,
        "reason": request.reason,
    })
    await manager.broadcast_event("TELEMETRY_LOG", {
        "agent": "Automated Containment Agent",
        "message": f"🛡️ Precision Isolation Executed by {current_user['username']}! Severed accounts: {', '.join(frozen_ids)}",
    })

    return {"status": "CONTAINED", "frozen_accounts": frozen_ids, "count": len(frozen_ids)}


@app.post("/api/v1/compliance/generate-sar")
async def generate_sar(
    request: SARRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generates a formal SAR narrative using Gemini based on SHAP risk drivers
    and graph topology context. Falls back gracefully on API errors/quota limits.
    """
    operator_name = current_user.get("username", "Analyst_Local")

    try:
        client = get_genai_client()

        prompt = f"""
        You are an automated FinCEN Compliance Officer AI integrated into an anti-money laundering platform.
        Generate a formal Suspicious Activity Report (SAR) narrative based on the following graph event details:
        - Target Account SHA-256 ID: {request.account_id}
        - Composite Risk Score: {request.risk_score}/100
        - Top Explainable AI (SHAP) Risk Drivers: {', '.join(request.shap_drivers)}
        - Detected Network Pattern / Typology: {request.detected_topology}

        Provide the response structured into 3 distinct sections:
        1. EXECUTIVE SUMMARY
        2. GRAPH TYPOLOGY & TRANSACTION PATTERN ANALYSIS
        3. RECOMMENDED REGULATORY MITIGATION & ASSET FREEZE ACTION
        """

        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        sar_text = response.text if response and hasattr(response, "text") else "Report generation complete."

        await manager.broadcast_event("TELEMETRY_LOG", {
            "agent": "Gemini Compliance Agent",
            "message": f"📄 SAR Narrative auto-drafted for account {request.account_id} by {operator_name}.",
        })

        return {
            "account_id": request.account_id,
            "sar_report": sar_text,
            "status": "DRAFTED_PENDING_REVIEW",
            "source": "gemini-api",
        }

    except (errors.APIError, Exception) as e:
        logger.warning(f"⚠️ Gemini API rate limited or API error: {str(e)}. Triggering local fallback SAR draft.")

        fallback_sar = (
            "================================================================================\n"
            "📄 SUSPICIOUS ACTIVITY REPORT (SAR) - DRAFT [LOCAL FALLBACK ENGINE]\n"
            "================================================================================\n"
            f"1. EXECUTIVE SUMMARY:\n"
            f"Target Account ID: {request.account_id}\n"
            f"Composite Risk Score: {request.risk_score}/100 [CRITICAL ALERT]\n"
            f"Primary SHAP Drivers: {', '.join(request.shap_drivers)}\n\n"
            f"2. GRAPH TYPOLOGY & TRANSACTION PATTERN ANALYSIS:\n"
            f"Detected Network Topology: {request.detected_topology}.\n"
            f"High-frequency structured layering activity detected across connected graph nodes.\n\n"
            f"3. RECOMMENDED REGULATORY MITIGATION & ASSET FREEZE ACTION:\n"
            f"Immediate execution of Minimum-Cut containment on node {request.account_id}. Freeze associated outbound channels.\n"
            "================================================================================"
        )

        await manager.broadcast_event("TELEMETRY_LOG", {
            "agent": "Gemini Compliance Agent (Fallback)",
            "message": f"📄 Local Fallback SAR draft served for account {request.account_id}.",
        })

        return {
            "account_id": request.account_id,
            "sar_report": fallback_sar,
            "status": "DRAFTED_PENDING_REVIEW",
            "source": "local-fallback",
        }


# --- Real-Time Telemetry Background Loop ---

async def telemetry_background_worker():
    """Periodically queries graph state and streams updates via WebSockets."""
    while True:
        try:
            cycles = detect_micro_layering_cycles()
            if cycles:
                await manager.broadcast_event("CYCLE_ALERT", {"cycles": cycles})

            # FIX: call the instance method on the singleton agent, not a
            # nonexistent module-level function.
            risk_suspects = risk_agent.analyze_and_score_accounts()
            if risk_suspects:
                await manager.broadcast_event("RISK_SCORES", {"suspects": risk_suspects})

        except Exception as e:
            logger.warning(f"⚠️ Telemetry worker error: {e}")

        await asyncio.sleep(3)


@app.on_event("startup")
async def startup_event():
    init_sqlite_db()
    asyncio.create_task(telemetry_background_worker())


# --- WebSocket Channel ---

async def _telemetry_ws_loop(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"📩 Message from UI client: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"⚠️ WebSocket error, disconnecting client: {e}")
        manager.disconnect(websocket)


@app.websocket("/ws")
async def websocket_endpoint_root(websocket: WebSocket):
    """Matches the frontend's default `ws://localhost:8000/ws`."""
    await _telemetry_ws_loop(websocket)


@app.websocket("/ws/telemetry")
async def websocket_endpoint_telemetry(websocket: WebSocket):
    """Kept for backwards compatibility with the original route."""
    await _telemetry_ws_loop(websocket)