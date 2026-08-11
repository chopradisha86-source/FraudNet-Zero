import networkx as nx

def calculate_cost_weighted_min_cut(graph: nx.DiGraph, source_node: str, target_node: str) -> dict:
    """
    Computes Minimum Cut where edge capacity = Account Balance / Reputation Weight.
    Prevents innocent high-value accounts from being severed accidentally.
    """
    # Build capacity graph where capacity = balance weight
    for u, v, data in graph.edges(data=True):
        src_balance = data.get("source_balance", 1000.0)
        # High balance = high capacity (cut penalty) -> Algorithm avoids severing clean users
        weight = max(src_balance, 100.0) if not data.get("is_suspicious", False) else 10.0
        graph[u][v]["capacity"] = weight

    try:
        cut_value, partition = nx.minimum_cut(graph, source_node, target_node)
        reachable, non_reachable = partition
        
        # Edges crossing the cut boundary to be frozen
        cutset = set()
        for u in reachable:
            for v in graph[u]:
                if v in non_reachable:
                    cutset.add((u, v))
                    
        return {
            "cut_value": cut_value,
            "nodes_to_freeze": list(non_reachable),
            "edges_to_sever": list(cutset),
            "collateral_impact_score": len(non_reachable) / len(graph.nodes)
        }
    except Exception as e:
        return {"error": str(e), "nodes_to_freeze": [], "edges_to_sever": []}