import os
import json
import time
import logging
from datetime import datetime
import numpy as np
from gqlalchemy import Memgraph
from google import genai
from google.genai.errors import APIError
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env
load_dotenv()

# Configure Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# Connect to running Memgraph container
memgraph = Memgraph(host="127.0.0.1", port=7687)


# ==============================================================================
# 1. REAL-TIME GCN INFERENCE & DYNAMIC THRESHOLD EVALUATOR
# ==============================================================================

class TransactionGCNInferenceEngine:
    def __init__(self):
        # Feature weights: [amount, device_risk, in_ring, community_mule_flag]
        self.weights = np.array([0.25, 0.35, 0.30, 0.10])
        self.bias = -0.10

    def extract_feature_vector(self, tx_amount: float, graph_features: dict) -> np.ndarray:
        """
        Encodes real-time transaction payload and Memgraph graph features 
        into a normalized numerical vector.
        """
        norm_amount = min(tx_amount / 10000.0, 1.0)
        device_risk = float(graph_features.get("device_risk_score", 0.0))
        in_ring = float(graph_features.get("in_laundering_ring", 0))
        dynamic_threshold = graph_features.get("detection_threshold", 0.50)
        community_risk_flag = 1.0 if dynamic_threshold < 0.50 else 0.0

        return np.array([norm_amount, device_risk, in_ring, community_risk_flag])

    def predict_fraud_probability(self, tx_amount: float, graph_features: dict) -> float:
        """
        Executes inference pass to generate a fraud probability score [0.0, 1.0].
        """
        features = self.extract_feature_vector(tx_amount, graph_features)
        raw_score = np.dot(features, self.weights) + self.bias
        probability = 1.0 / (1.0 + np.exp(-raw_score * 5.0))
        return float(np.round(probability, 4))

# Instantiate global scoring engine
gcn_model = TransactionGCNInferenceEngine()


def analyze_transaction_with_agent(enriched_event: dict) -> dict:
    """
    Evaluates incoming streaming transactions against the GCN model and 
    compares predictions against the dynamic detection threshold (0.35 vs 0.50).
    """
    tx_id = enriched_event.get("transaction_id", "N/A")
    amount = float(enriched_event.get("amount", 0.0))
    sender_id = enriched_event.get("sender_id")
    graph_features = enriched_event.get("sender_graph_features", {})

    # 1. Run inference scoring pass
    fraud_probability = gcn_model.predict_fraud_probability(amount, graph_features)

    # 2. Extract dynamic threshold (0.35 for high-risk neighborhoods, else 0.50)
    dynamic_threshold = graph_features.get("detection_threshold", 0.50)
    in_ring = graph_features.get("in_laundering_ring", 0)

    # 3. Decision threshold check
    is_suspicious = fraud_probability >= dynamic_threshold

    # 4. Stream-level logging
    if is_suspicious:
        logger.info(
            f"🚨 [LLM/GCN Agent] FLAGGED TX: {tx_id} | Sender: {sender_id} | "
            f"Prob: {fraud_probability:.2f} >= Threshold: {dynamic_threshold:.2f} | "
            f"In Ring: {bool(in_ring)}"
        )
    else:
        print(
            f"🟢 [LLM/GCN Agent] PASSED TX: {tx_id} | Sender: {sender_id} | "
            f"Prob: {fraud_probability:.2f} < Threshold: {dynamic_threshold:.2f}",
            end="\r"
        )

    return {
        "transaction_id": tx_id,
        "sender_id": sender_id,
        "fraud_probability": fraud_probability,
        "threshold_applied": dynamic_threshold,
        "flagged": is_suspicious
    }


# ==============================================================================
# 2. FORENSIC EVIDENCE EXTRACTION & SAR NARRATIVE GENERATION
# ==============================================================================

def fetch_account_forensics(account_id):
    """
    Retrieves full 1-hop graph context for a suspect account
    """
    query = """
    MATCH (a:Account {id: $account_id})-[r:TRANSFERRED]-(b:Account)
    RETURN a.id AS suspect_id,
           collect(DISTINCT b.id) AS connected_accounts,
           collect(DISTINCT r.ip) AS used_ips,
           collect(DISTINCT r.device) AS used_devices,
           sum(r.amount) AS total_volume,
           count(r) AS tx_count
    LIMIT 1
    """
    try:
        results = list(memgraph.execute_and_fetch(query, {"account_id": account_id}))
        if results:
            return results[0]
        return None
    except Exception as e:
        logger.error(f"❌ Error fetching forensics: {e}")
        return None

def generate_sar_summary(forensics):
    """
    Generates a structured forensic summary narrative using the official google-genai SDK.
    Uses active model aliases to bypass tier deprecation rules.
    """
    if not client:
        logger.error("❌ Gemini client initialized without API key.")
        return "Error: GEMINI_API_KEY missing from environment variables."

    suspect = forensics["suspect_id"]
    volume = forensics["total_volume"]
    tx_count = forensics["tx_count"]
    peers = forensics["connected_accounts"]
    ips = forensics["used_ips"]
    devices = forensics["used_devices"]

    prompt = f"""
    You are a Lead Financial Crime Compliance Investigator. Analyze the following Memgraph forensic data for target account {suspect}:

    - Target Account ID: {suspect}
    - Total Volume Transacted: ${volume:,.2f} USD across {tx_count} transactions
    - Connected Peer Nodes: {len(peers)} accounts ({', '.join(peers[:5]) if peers else 'None'})
    - Device Fingerprints: {', '.join(devices) if devices else 'None'}
    - IP Footprint: {', '.join(ips) if ips else 'None'}

    Write an official, high-precision Suspicious Activity Report (SAR) narrative formatted cleanly with the following headings:
    1. SUMMARY STATEMENT
    2. KEY EVIDENCE & TOPOLOGY
    3. FORENSIC NARRATIVE (Analyze velocity layering, IP/Device overlap, and money laundering indicators)
    4. RECOMMENDED COMPLIANCE ACTION
    """

    # Priority queue of active Gemini models
    candidates = ["gemini-flash-latest", "gemini-2.5-pro", "gemini-3.6-flash"]

    for model_name in candidates:
        try:
            time.sleep(1)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            return response.text
        except APIError as e:
            logger.warning(f"⚠️ Model target '{model_name}' failed ({str(e)}). Trying next candidate...")
            continue
        except Exception as e:
            logger.warning(f"⚠️ Exception on '{model_name}' ({str(e)}). Trying next candidate...")
            continue

    logger.warning("⚠️ All API candidates exhausted. Serving fallback SAR draft.")
    return f"""
================================================================================
📄 AUTOMATED SUSPICIOUS ACTIVITY REPORT (SAR) [FALLBACK ENGINE]
================================================================================
Target Subject ID : {suspect}
Risk Assessment   : CRITICAL (Automated FraudNet-Zero Alert)
Total Volume      : ${volume:,.2f} USD ({tx_count} transactions)

🔍 KEY EVIDENCE & TOPOLOGY:
  • Connected Nodes  : {len(peers)} peers ({', '.join(peers[:3]) if peers else 'None'})
  • Shared Hardware  : Devices [{', '.join(devices) if devices else 'None'}]
  • IP Footprint     : IPs [{', '.join(ips) if ips else 'None'}]

RECOMMENDED ACTION: Freeze target account immediately and initiate legal audit.
================================================================================
"""

def save_sar_to_disk(suspect_id: str, sar_content: str):
    """
    Persists the generated SAR markdown narrative to local storage.
    """
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(reports_dir, f"SAR_{suspect_id}_{timestamp}.md")
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(sar_content)
        print(f"\n💾 SAR report successfully persisted to: {filepath}\n")
    except Exception as e:
        logger.error(f"❌ Failed to save SAR report to disk: {e}")

def run_llm_agent():
    print("🤖 Explainable AI / SAR Forensic Agent Active...\n")
    
    top_query = """
    MATCH (a:Account)-[r:TRANSFERRED]->()
    WITH a.id AS suspect_id, count(r) AS cnt
    ORDER BY cnt DESC
    RETURN suspect_id
    LIMIT 1
    """
    
    try:
        results = list(memgraph.execute_and_fetch(top_query))
        if results:
            top_suspect = results[0]["suspect_id"]
            print(f"🔎 Pulling deep forensic evidence for primary suspect: {top_suspect}...\n")
            
            forensics = fetch_account_forensics(top_suspect)
            if forensics:
                sar = generate_sar_summary(forensics)
                print(sar)
                save_sar_to_disk(top_suspect, sar)
            else:
                print("⚠️ No forensic data found for suspect.")
        else:
            print("⚠️ Waiting for streaming data to register high-risk nodes...")
    except Exception as e:
        print(f"❌ Error running SAR agent: {e}")

if __name__ == "__main__":
    run_llm_agent()