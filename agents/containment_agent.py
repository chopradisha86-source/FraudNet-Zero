"""
DIFF FROM ORIGINAL: `calculate_cost_weighted_min_cut` is unchanged.
Added `build_graph_from_subgraph_rows` and `run_containment_pipeline`.

FIX (integration gap): the min-cut function existed but nothing in the
API layer ever called it — `/api/v1/containment/execute` just froze
whatever account_ids the frontend sent, with no actual graph analysis
behind it. `run_containment_pipeline` is the missing glue: it pulls a
live subgraph from Memgraph (via topology_agent) and runs the min-cut
against it, returning cut-edges the frontend can render in red before
anything is frozen.
"""
import networkx as nx


def calculate_cost_weighted_min_cut(graph: nx.DiGraph, source_node: str, target_node: str) -> dict:
    """
    Computes Minimum Cut where edge capacity = Account Balance / Reputation Weight.
    Prevents innocent high-value accounts from being severed accidentally.
    """
    for u, v, data in graph.edges(data=True):
        src_balance = data.get("source_balance", 1000.0)
        weight = max(src_balance, 100.0) if not data.get("is_suspicious", False) else 10.0
        graph[u][v]["capacity"] = weight

    try:
        cut_value, partition = nx.minimum_cut(graph, source_node, target_node)
        reachable, non_reachable = partition

        cutset = set()
        for u in reachable:
            for v in graph[u]:
                if v in non_reachable:
                    cutset.add((u, v))

        return {
            "cut_value": cut_value,
            "nodes_to_freeze": list(non_reachable),
            "edges_to_sever": list(cutset),
            "collateral_impact_score": len(non_reachable) / len(graph.nodes),
        }
    except Exception as e:
        return {"error": str(e), "nodes_to_freeze": [], "edges_to_sever": []}


def build_graph_from_subgraph_rows(rows: list) -> nx.DiGraph:
    """Converts Memgraph query rows (from extract_subgraph_for_containment) into a nx.DiGraph."""
    G = nx.DiGraph()
    for row in rows:
        G.add_edge(
            row["source"],
            row["target"],
            amount=row.get("amount", 0.0),
            source_balance=row.get("source_balance", 1000.0),
            is_suspicious=row.get("is_suspicious", False),
        )
    return G


def run_containment_pipeline(target_account_id: str, sink_account_id: str, hops: int = 2) -> dict:
    """
    End-to-end containment analysis: pulls a live neighborhood subgraph around
    `target_account_id` from Memgraph, builds a capacitated flow graph, and
    computes the minimum cut needed to sever fraudulent flow from
    `target_account_id` (source) to `sink_account_id` (sink).

    Returns the same shape as calculate_cost_weighted_min_cut, plus an
    `error` key on failure (empty subgraph, source/sink not connected, etc.)
    """
    from gcn_core.topology_agent import extract_subgraph_for_containment

    rows = extract_subgraph_for_containment(target_account_id, hops=hops)
    if not rows:
        return {
            "error": f"No transaction subgraph found around '{target_account_id}'.",
            "nodes_to_freeze": [],
            "edges_to_sever": [],
        }

    graph = build_graph_from_subgraph_rows(rows)

    if target_account_id not in graph.nodes:
        return {
            "error": f"Source node '{target_account_id}' not present in extracted subgraph.",
            "nodes_to_freeze": [],
            "edges_to_sever": [],
        }
    if sink_account_id not in graph.nodes:
        return {
            "error": f"Sink node '{sink_account_id}' not present in extracted subgraph. "
                     f"Try a larger hop radius or a different sink account.",
            "nodes_to_freeze": [],
            "edges_to_sever": [],
        }

    return calculate_cost_weighted_min_cut(graph, target_account_id, sink_account_id)