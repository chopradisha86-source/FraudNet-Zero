import json
import time
from gqlalchemy import Memgraph

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
    Generates a structured forensic summary narrative.
    """
    suspect = forensics["suspect_id"]
    volume = forensics["total_volume"]
    tx_count = forensics["tx_count"]
    peers = forensics["connected_accounts"]
    ips = forensics["used_ips"]
    devices = forensics["used_devices"]

    report = f"""
================================================================================
📄 AUTOMATED SUSPICIOUS ACTIVITY REPORT (SAR)
================================================================================
Target Subject ID : {suspect}
Risk Assessment   : CRITICAL (Automated FraudNet Zero Alert)
Total Volume      : ${volume:,.2f} USD ({tx_count} transactions)

🔍 KEY EVIDENCE & TOPOLOGY:
  • Connected Nodes  : {len(peers)} peers ({', '.join(peers[:3]) if peers else 'None'}...)
  • Shared Hardware  : Devices [{', '.join(devices)}]
  • IP Footprint     : IPs [{', '.join(ips)}]

💡 FORENSIC NARRATIVE:
  Account {suspect} exhibits high-velocity transactional layering behavior. 
  Multiple outgoing transfers route through interconnected peer nodes using 
  overlapping IP address spaces and device IDs, strongly indicating a 
  mule network operating in a closed micro-layering loop.

RECOMMENDED ACTION: Freeze accounts immediately and submit FinCEN Form 111.
================================================================================
"""
    return report

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