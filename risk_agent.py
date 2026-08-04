import time
from gqlalchemy import Memgraph
import numpy as np

# Connect to running Memgraph container
memgraph = Memgraph(host="127.0.0.1", port=7687)

def calculate_shap_attributions(tx_count, in_ring, multi_device_ip):
    """
    Computes mock SHAP TreeExplainer feature attributions for risk scoring explainability.
    Returns the top 5 feature attributions as percentage impacts.
    """
    base_ring_impact = 0.45 if in_ring else 0.05
    velocity_impact = min(0.35, tx_count * 0.08)
    hardware_impact = 0.25 if multi_device_ip else 0.10

    features = [
        {"feature": "Graph Ring Topology", "impact_score": base_ring_impact, "percentage": f"{round(base_ring_impact * 100, 1)}%"},
        {"feature": "Transaction Velocity Spike", "impact_score": velocity_impact, "percentage": f"{round(velocity_impact * 100, 1)}%"},
        {"feature": "Device/IP Fingerprint Jump", "impact_score": hardware_impact, "percentage": f"{round(hardware_impact * 100, 1)}%"},
        {"feature": "Burst Ratio Anomaly", "impact_score": 0.08, "percentage": "8.0%"},
        {"feature": "Account Dormancy Reactivation", "impact_score": 0.04, "percentage": "4.0%"}
    ]

    # Sort by absolute impact score
    sorted_features = sorted(features, key=lambda x: x["impact_score"], reverse=True)
    return sorted_features[:5]

def evaluate_model_performance(y_true, y_pred_probs, threshold=0.5):
    """
    Evaluates risk scoring performance using Recall-Weighted F2-Score (Beta=2.0)
    to minimize undetected fraud rings in imbalanced datasets.
    """
    try:
        from sklearn.metrics import fbeta_score
        y_pred = (np.array(y_pred_probs) >= threshold).astype(int)
        f2 = fbeta_score(y_true, y_pred, beta=2.0)
        return float(round(f2, 4))
    except Exception:
        return 0.0

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
    WITH a, tx_count, ips, devices, (ring_path IS NOT NULL) AS in_ring,
         (size(ips) > 1 OR size(devices) > 1) AS multi_device_ip
    
    // Calculate composite risk score
    WITH a, tx_count, in_ring, multi_device_ip,
         (CASE WHEN in_ring THEN 45 ELSE 0 END) +
         (CASE WHEN tx_count > 3 THEN 30 ELSE tx_count * 8 END) +
         (CASE WHEN multi_device_ip THEN 25 ELSE 10 END) AS raw_score
         
    WITH a, raw_score, tx_count, in_ring, multi_device_ip,
         CASE 
           WHEN raw_score >= 75 THEN 'CRITICAL'
           WHEN raw_score >= 50 THEN 'HIGH'
           WHEN raw_score >= 25 THEN 'MEDIUM'
           ELSE 'LOW'
         END AS risk_level

    // Update risk score properties back to Memgraph nodes
    SET a.risk_score = raw_score, a.risk_level = risk_level
    
    RETURN a.id AS account_id, 
           raw_score AS risk_score,
           risk_level,
           tx_count,
           in_ring,
           multi_device_ip
    ORDER BY risk_score DESC
    LIMIT 10;
    """
    try:
        results = list(memgraph.execute_and_fetch(query))
        
        # Enrich results with SHAP attributions for explainability
        for row in results:
            row["shap_attributions"] = calculate_shap_attributions(
                row["tx_count"], 
                row["in_ring"], 
                row["multi_device_ip"]
            )
            
        return results
    except Exception as e:
        print(f"❌ Error computing risk scores: {e}")
        return []

def run_risk_agent():
    print("🛡️ Risk Scoring Agent Active...")
    print("Evaluating real-time composite risk scores & SHAP feature attributions...\n")
    
    try:
        while True:
            scores = analyze_and_score_accounts()
            if scores:
                print("================ 🚨 TOP RISK SUSPECTS 🚨 ================")
                for row in scores:
                    acc = row["account_id"]
                    score = row["risk_score"]
                    level = row["risk_level"]
                    top_shap = row["shap_attributions"][0]["feature"] if row.get("shap_attributions") else "N/A"
                    
                    badge = "🔴" if level == "CRITICAL" else ("🟠" if level == "HIGH" else "🟡")
                    print(f"{badge} Account: {acc:<16} | Score: {score:>3}/100 | Level: {level:<8} | Top Driver: {top_shap}")
                print("=========================================================\n")
            else:
                print("🟢 Monitoring account risk profiles...", end="\r")
            
            time.sleep(4)
            
    except KeyboardInterrupt:
        print("\nStopping Risk Scoring Agent...")

if __name__ == "__main__":
    run_risk_agent()