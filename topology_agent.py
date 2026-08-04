import time
from gqlalchemy import Memgraph

# Connect to Memgraph
memgraph = Memgraph(host="127.0.0.1", port=7687)

def run_louvain_community_analysis():
    """
    Executes Louvain community detection and sets dynamic thresholds 
    for accounts in high-risk communities (>30% fraud density).
    """
    try:
        # 1. Execute Louvain Community Detection query in Cypher
        louvain_query = """
        CALL louvain.get() YIELD node, community_id
        SET node.community_id = community_id;
        """
        memgraph.execute(louvain_query)

        # 2. Calculate community fraud density & lower threshold for high-risk clusters
        density_query = """
        MATCH (a:Account)
        WITH a.community_id AS community, 
             count(a) AS total_nodes, 
             sum(CASE WHEN a.risk_score > 0.7 THEN 1 ELSE 0 END) AS flagged_nodes
        WITH community, (toFloat(flagged_nodes) / total_nodes) AS community_mule_density
        WHERE community_mule_density > 0.30
        MATCH (a:Account {community_id: community})
        SET a.detection_threshold = 0.35;
        """
        memgraph.execute(density_query)
        print("📊 [Topology Agent] Louvain Community Density Scoring Complete.")
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

        # Run Louvain Community Analysis every 10 iterations (~30 seconds)
        cycle_check_counter += 1
        if cycle_check_counter % 10 == 0:
            run_louvain_community_analysis()
            
        time.sleep(3)

if __name__ == "__main__":
    run_topology_agent()