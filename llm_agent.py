import os
import json
import time
from gqlalchemy import Memgraph
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Configure Gemini with API Key from .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Connect to running Memgraph container
memgraph = Memgraph(host="127.0.0.1", port=7687)

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
        print(f"❌ Error fetching forensics: {e}")
        return None

def generate_sar_summary(forensics):
    """
    Generates a structured forensic summary narrative using Gemini 1.5 Flash.
    """
    suspect = forensics["suspect_id"]
    volume = forensics["total_volume"]
    tx_count = forensics["tx_count"]
    peers = forensics["connected_accounts"]
    ips = forensics["used_ips"]
    devices = forensics["used_devices"]

    # Use active model
    model = genai.GenerativeModel("gemini-1.5-flash")

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

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"❌ Gemini Generation Error: {e}")
        # Fallback template if API fails
        return f"""
================================================================================
📄 AUTOMATED SUSPICIOUS ACTIVITY REPORT (SAR) [FALLBACK]
================================================================================
Target Subject ID : {suspect}
Risk Assessment   : CRITICAL (Automated FraudNet Zero Alert)
Total Volume      : ${volume:,.2f} USD ({tx_count} transactions)

🔍 KEY EVIDENCE & TOPOLOGY:
  • Connected Nodes  : {len(peers)} peers ({', '.join(peers[:3]) if peers else 'None'})
  • Shared Hardware  : Devices [{', '.join(devices)}]
  • IP Footprint     : IPs [{', '.join(ips)}]

RECOMMENDED ACTION: Freeze accounts immediately and submit FinCEN Form 111.
================================================================================
"""

def run_llm_agent():
    print("🤖 Explainable AI / SAR Forensic Agent Active...\n")
    
    # Query top critical account returning raw scalar properties directly
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
            else:
                print("⚠️ No forensic data found for suspect.")
        else:
            print("⚠️ Waiting for streaming data to register high-risk nodes...")
    except Exception as e:
        print(f"❌ Error running SAR agent: {e}")

if __name__ == "__main__":
    run_llm_agent()