import time
from gqlalchemy import Memgraph

# Connect to Memgraph
memgraph = Memgraph(host="127.0.0.1", port=7687)

def detect_micro_layering_cycles():
    """
    Scans Memgraph for circular fund transfers (A -> B -> C -> A) 
    indicating money laundering rings.
    """
    # Using size() for Memgraph compatibility
    query = """
    MATCH path = (a:Account)-[:TRANSFERRED*3..6]->(a)
    WITH path, nodes(path) AS cycle_nodes
    UNWIND cycle_nodes AS n
    WITH path, collect(n.id) AS node_ids
    RETURN DISTINCT node_ids, size(node_ids) - 1 AS ring_length
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
    print("Monitoring graph database for micro-layering cycles...\n")
    
    while True:
        cycles = detect_micro_layering_cycles()
        
        if cycles:
            print(f"🚨 ALERT: Detected {len(cycles)} Laundering Cycles in Graph!")
            for idx, cycle in enumerate(cycles, 1):
                ring = " ➔ ".join(cycle["node_ids"])
                print(f"  [{idx}] Ring Length: {cycle['ring_length']} | Path: {ring}")
        else:
            print("🟢 No active laundering cycles detected in current window.", end="\r")
            
        time.sleep(3)

if __name__ == "__main__":
    run_topology_agent()