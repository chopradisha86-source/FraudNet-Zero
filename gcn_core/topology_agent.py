"""
DIFF FROM ORIGINAL: only `extract_subgraph_for_containment` changed.

FIX (integration gap): the original query returned `source_risk` /
`target_risk` but not `source_balance` or `is_suspicious`. Those two
fields are exactly what `containment_agent.calculate_cost_weighted_min_cut`
reads via `data.get("source_balance", ...)` / `data.get("is_suspicious", ...)`.
Without them every edge silently fell back to default capacity (1000.0),
so the min-cut was never actually risk-weighted in practice.

Everything else in this file is unchanged from your original
topology_agent.py — copy this whole file over the old one, or just
replace the `extract_subgraph_for_containment` function.
"""
import time
from gqlalchemy import Memgraph

# Connect to running Memgraph container
memgraph = Memgraph(host="127.0.0.1", port=7687)


def inject_synthetic_ring(ring_size: int = 4, base_amount: float = 9500.0) -> list:
    """
    Generates and executes Cypher queries to inject a synthetic multi-node
    laundering ring (A -> B -> C -> D -> A) into Memgraph over standard PaySim data.
    """
    timestamp = int(time.time())
    mules = [f"MULE_{timestamp}_{i}" for i in range(ring_size)]

    print(f"\n⚡ [Topology Agent] Injecting {ring_size}-Node Synthetic Ring: {' ➔ '.join(mules)}")

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
        community_query = """
        MATCH (a:Account)
        WHERE a.community_id IS NULL
        SET a.community_id = id(a);
        """
        memgraph.execute(community_query)

        density_query = """
        MATCH (a:Account)
        WHERE coalesce(a.risk_score, 0.0) > 0.7
        SET a.detection_threshold = 0.35;
        """
        memgraph.execute(density_query)
        print("\n📊 [Topology Agent] Community Density Scoring Complete.")
    except Exception as e:
        print(f"⚠️ [Topology Agent] Community analysis warning/notice: {e}")


def detect_micro_layering_cycles() -> list:
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
        return list(memgraph.execute_and_fetch(query))
    except Exception as e:
        print(f"\n❌ Error executing cycle detection query: {e}")
        return []


def extract_account_graph_features(account_id: str) -> dict:
    """
    Queries Memgraph for dynamic topology metrics and laundering cycle flags
    for a given account ID to supply downstream ML models.
    """
    query = f"""
    MATCH (a:Account {{id: '{account_id}'}})
    OPTIONAL MATCH ring_path = (a)-[:TRANSFERRED*3..6]->(a)
    RETURN
        coalesce(a.risk_score, 0.0) AS device_risk_score,
        coalesce(a.balance, 0.0) AS account_balance,
        coalesce(a.community_id, -1) AS louvain_community_id,
        coalesce(a.detection_threshold, 0.5) AS detection_threshold,
        CASE WHEN ring_path IS NOT NULL THEN 1 ELSE 0 END AS in_laundering_ring
    LIMIT 1
    """
    default = {
        "device_risk_score": 0.0,
        "account_balance": 0.0,
        "louvain_community_id": -1,
        "detection_threshold": 0.5,
        "in_laundering_ring": 0,
    }
    try:
        results = list(memgraph.execute_and_fetch(query))
        return results[0] if results else default
    except Exception as e:
        print(f"\n❌ Error fetching graph features for {account_id}: {e}")
        return default


def extract_subgraph_for_containment(target_account_id: str, hops: int = 2) -> list:
    """
    Extracts localized neighborhood subgraph for containment_agent.py (Min-Cut Engine).

    FIXED: now returns `source_balance` and `is_suspicious` directly, matching
    what calculate_cost_weighted_min_cut expects — previously these fields
    were missing and every edge fell back to default capacity.
    """
    query = f"""
    MATCH path = (a:Account {{id: '{target_account_id}'}})-[:TRANSFERRED*1..{hops}]-(b:Account)
    UNWIND relationships(path) AS rel
    RETURN
        startNode(rel).id AS source,
        endNode(rel).id AS target,
        coalesce(rel.amount, 0.0) AS amount,
        coalesce(startNode(rel).balance, 1000.0) AS source_balance,
        coalesce(startNode(rel).risk_score, 0.0) AS source_risk,
        coalesce(endNode(rel).risk_score, 0.0) AS target_risk,
        (coalesce(startNode(rel).risk_score, 0.0) > 0.7) AS is_suspicious
    """
    try:
        return list(memgraph.execute_and_fetch(query))
    except Exception as e:
        print(f"\n❌ Error extracting subgraph for containment: {e}")
        return []


def run_topology_agent():
    print("🕵️ Network Topology Agent Active...")
    print("Monitoring graph database for micro-layering cycles & community clusters...\n")

    cycle_check_counter = 0

    try:
        while True:
            cycles = detect_micro_layering_cycles()

            if cycles:
                print(f"\n🚨 ALERT: Detected {len(cycles)} Laundering Cycles in Graph!")
                for idx, cycle in enumerate(cycles, 1):
                    ring = " ➔ ".join(cycle["node_ids"])
                    print(f"   [{idx}] Ring Length: {cycle['ring_length']} | Path: {ring}")
            else:
                print("🟢 No active laundering cycles detected in current window.", end="\r")

            cycle_check_counter += 1
            if cycle_check_counter % 10 == 0:
                run_louvain_community_analysis()

            time.sleep(3)

    except KeyboardInterrupt:
        print("\nStopping Network Topology Agent...")


if __name__ == "__main__":
    run_topology_agent()