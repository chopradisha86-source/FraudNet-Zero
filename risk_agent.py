import time
from gqlalchemy import Memgraph

# Connect to running Memgraph container
memgraph = Memgraph(host="127.0.0.1", port=7687)

def analyze_and_score_accounts():
    """
    Evaluates accounts across the graph for multi-factor risk indicators:
    - Cycle participation (Laundering topology)
    - IP/Device sharing (Mule network hardware fingerprint)
    - High transfer frequency (Rapid layering)
    """
    query = """
    MATCH (a:Account)-[r:TRANSFERRED]->(b:Account)
    WITH a, count(r) AS tx_count, collect(r.ip) AS ips, collect(r.device) AS devices
    
    // 1. Check if node is part of a laundering ring
    OPTIONAL MATCH ring_path = (a)-[:TRANSFERRED*3..6]->(a)
    WITH a, tx_count, ips, devices, (ring_path IS NOT NULL) AS in_ring
    
    // Calculate composite risk score
    WITH a,
         (CASE WHEN in_ring THEN 45 ELSE 0 END) +
         (CASE WHEN tx_count > 3 THEN 30 ELSE tx_count * 8 END) +
         (CASE WHEN size(ips) > 1 OR size(devices) > 1 THEN 25 ELSE 10 END) AS raw_score
         
    RETURN a.id AS account_id, 
           raw_score AS risk_score,
           CASE 
             WHEN raw_score >= 75 THEN 'CRITICAL'
             WHEN raw_score >= 50 THEN 'HIGH'
             WHEN raw_score >= 25 THEN 'MEDIUM'
             ELSE 'LOW'
           END AS risk_level
    ORDER BY risk_score DESC
    LIMIT 10;
    """
    try:
        results = memgraph.execute_and_fetch(query)
        return list(results)
    except Exception as e:
        print(f"❌ Error computing risk scores: {e}")
        return []

def run_risk_agent():
    print("🛡️ Risk Scoring Agent Active...")
    print("Evaluating real-time composite risk scores across active accounts...\n")
    
    try:
        while True:
            scores = analyze_and_score_accounts()
            if scores:
                print("================ 🚨 TOP RISK SUSPECTS 🚨 ================")
                for row in scores:
                    acc = row["account_id"]
                    score = row["risk_score"]
                    level = row["risk_level"]
                    
                    badge = "🔴" if level == "CRITICAL" else ("🟠" if level == "HIGH" else "🟡")
                    print(f"{badge} Account: {acc:<15} | Risk Score: {score}/100 | Level: {level}")
                print("=========================================================\n")
            else:
                print("🟢 Monitoring account risk profiles...", end="\r")
            
            time.sleep(4)
            
    except KeyboardInterrupt:
        print("\nStopping Risk Scoring Agent...")

if __name__ == "__main__":
    run_risk_agent()