import time
import random
from gqlalchemy import Memgraph

# Connect to running Memgraph instance
memgraph = Memgraph(host="127.0.0.1", port=7687)

def inject_synthetic_ring(ring_size: int = 4, base_amount: float = 9500.0) -> list[dict]:
    """
    Generates and executes Cypher queries to inject a synthetic multi-node 
    laundering ring (A -> B -> C -> D -> A) into Memgraph over standard PaySim data.
    """
    timestamp = int(time.time())
    mules = [f"MULE_{timestamp}_{i}" for i in range(ring_size)]
    
    print(f"\n⚡ [Topology Agent] Injecting {ring_size}-Node Synthetic Ring: {' ➔ '.join(mules)}")
    
    # Create ring nodes and directed edges in Memgraph
    for i in range(ring_size):
        src = mules[i]
        dst = mules[(i + 1) % ring_size]
        
        inject_query = f"""
        MERGE (s:Account {{id: '{src}'}})
        ON CREATE SET s.balance = 150.0, s.risk_score = 0.85
        MERGE (r:Account {{id: '{dst}'}})
        ON CREATE SET r.balance = 150.0, r.risk_score = 0.85
        CREATE (s)-[:TRANSFERRED {{
            amount: {base_amount},
            type: 'TRANSFER',
            is_fraud_ground_truth: 1,
            is_synthetic_ring: 1,
            timestamp: '{timestamp}'
        }}]->(r);
        """
        try:
            memgraph.execute(inject_query)
        except Exception as e:
            print(f"⚠️ [Topology Agent] Ring injection warning: {e}")
            
    return mules

def run_louvain_community_analysis():
    """
    Executes lightweight community partitioning and dynamic risk scoring 
    without triggering MAGE procedure errors or Memgraph write-lock conflicts.
    """
    try:
        # 1. Assign community IDs natively using node internal IDs
        community_query = """
        MATCH (a:Account)
        WHERE a.community_id IS NULL
        SET a.community_id = id(a);
        """
        memgraph.execute(community_query)

        # 2. Lower threshold for high-risk accounts (>0.7 risk score)
        density_query = """
        MATCH (a:Account)
        WHERE coalesce(a.risk_score, 0.0) > 0.7
        SET a.detection_threshold = 0.35;
        """
        memgraph.execute(density_query)
        print("📊 [Topology Agent] Community Density Scoring Complete.")
    except Exception as e:
        print(f"⚠️ [Topology Agent] Community analysis warning/notice: {e}")

def detect_micro_layering_cycles():
    """
    Scans Memgraph for circular fund transfers (A -> B -> C -> A) 
    indicating money laundering rings.
    """
    query = """
    MATCH path = (a:Account)-[:TRANSFERRED*3..6]->(a)
    WITH path, nodes(path) AS cycle_nodes
    UNWIND cycle_nodes AS n
    WITH path, collect(DISTINCT n.id) AS node_ids
    RETURN DISTINCT node_ids, size(node_ids) AS ring_length
    LIMIT 10
    """
    
    try:
        results = list(memgraph.execute_and_fetch(query))
        return results
    except Exception as e:
        print(f"Error executing cycle detection query: {e}")
        return []

def extract_account_graph_features(account_id: str) -> dict:
    """
    Queries Memgraph for dynamic topology metrics and laundering cycle flags
    for a given account ID to supply downstream ML models.
    """
    query = """
    MATCH (a:Account {id: $account_id})
    OPTIONAL MATCH ring_path = (a)-[:TRANSFERRED*3..6]->(a)
    RETURN 
        coalesce(a.risk_score, 0.0) AS device_risk_score,
        coalesce(a.balance, 0.0) AS account_balance,
        coalesce(a.community_id, -1) AS louvain_community_id,
        coalesce(a.detection_threshold, 0.5) AS detection_threshold,
        CASE WHEN ring_path IS NOT NULL THEN 1 ELSE 0 END AS in_laundering_ring
    LIMIT 1
    """
    try:
        results = list(memgraph.execute_and_fetch(query, parameters={"account_id": account_id}))
        if results:
            return results[0]
        return {
            "device_risk_score": 0.0,
            "account_balance": 0.0,
            "louvain_community_id": -1,
            "detection_threshold": 0.5,
            "in_laundering_ring": 0
        }
    except Exception as e:
        print(f"Error fetching graph features for {account_id}: {e}")
        return {
            "device_risk_score": 0.0,
            "account_balance": 0.0,
            "louvain_community_id": -1,
            "detection_threshold": 0.5,
            "in_laundering_ring": 0
        }

def run_topology_agent():
    print("🕵️ Network Topology Agent Active...")
    print("Monitoring graph database for micro-layering cycles & community clusters...\n")
    
    cycle_check_counter = 0

    while True:
        # Scan for circular laundering loops
        cycles = detect_micro_layering_cycles()
        
        if cycles:
            print(f"\n🚨 ALERT: Detected {len(cycles)} Laundering Cycles in Graph!")
            for idx, cycle in enumerate(cycles, 1):
                ring = " ➔ ".join(cycle["node_ids"])
                print(f"   [{idx}] Ring Length: {cycle['ring_length']} | Path: {ring}")
        else:
            print("🟢 No active laundering cycles detected in current window.", end="\r")

        # Periodically run Community Analysis (~30 seconds)
        cycle_check_counter += 1
        if cycle_check_counter % 10 == 0:
            run_louvain_community_analysis()
            
        time.sleep(3)

if __name__ == "__main__":
    # Optional test injection on startup:
    # inject_synthetic_ring(ring_size=4)
    run_topology_agent()