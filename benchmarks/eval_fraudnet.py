"""
FraudNet-Zero — Detection Evaluation Harness
==============================================

WHAT THIS IS
------------
A self-contained, honest benchmark for the ring-detection logic in
`topology_agent.py`. It does NOT require a running Memgraph instance —
it reimplements the exact same rule your Cypher query uses

    MATCH path = (a)-[:TRANSFERRED*3..6]->(a)

as a NetworkX elementary-cycle search of length 3–6, so the numbers this
produces are a faithful measurement of your actual detection rule, not
a toy stand-in for it. (If you want to validate it against live
Memgraph too, see `verify_against_memgraph()` at the bottom — same
ground truth, same query your app actually runs.)

METHODOLOGY
-----------
1. Build a "clean" transaction graph of M accounts with random transfers
   (Erdos-Renyi-style directed edges) — this is the honest part: some
   clean accounts WILL accidentally form 3-6-length cycles by chance,
   which is exactly the source of real false positives in a production
   system, so we don't get to pretend that away.
2. Inject N synthetic laundering rings (cycle length 3-6, matching
   `producer.py`'s `produce_laundering_ring` pattern) with unique
   MULE_ account IDs — these are ground-truth fraud accounts.
3. Run the detector (cycle search, length 3-6) over the combined graph.
4. Score at the ACCOUNT level: an account is a predicted positive if it
   appears in any detected cycle.
5. Report Precision, Recall, False Positive Rate, and F1, averaged over
   multiple random trials for stability.

HOW TO RUN
----------
    python eval_fraudnet.py

Tune the constants under `if __name__ == "__main__"` to match the scale
you want to report (e.g. larger M to see how FPR behaves at higher
transaction volume).
"""
import random
import statistics
from dataclasses import dataclass, field

import networkx as nx


@dataclass
class EvalResult:
    trial: int
    total_accounts: int
    fraud_accounts: int
    clean_accounts: int
    predicted_positive: int
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int
    precision: float
    recall: float
    false_positive_rate: float
    f1: float


def build_clean_graph(num_accounts: int, avg_out_degree: float, seed: int) -> nx.DiGraph:
    """Random directed transaction graph simulating ordinary account activity."""
    rng = random.Random(seed)
    G = nx.DiGraph()
    accounts = [f"ACC_{i:05d}" for i in range(num_accounts)]
    G.add_nodes_from(accounts)

    num_edges = int(num_accounts * avg_out_degree)
    for _ in range(num_edges):
        src, dst = rng.sample(accounts, 2)
        G.add_edge(src, dst, amount=round(rng.uniform(10, 5000), 2), is_synthetic_ring=False)

    return G


def inject_fraud_rings(G: nx.DiGraph, num_rings: int, ring_size_range: tuple, seed: int) -> set:
    """
    Injects directed cycles matching producer.py's produce_laundering_ring
    pattern. Returns the set of ground-truth fraud account IDs.
    """
    rng = random.Random(seed + 1)
    fraud_accounts = set()

    for r in range(num_rings):
        ring_size = rng.randint(*ring_size_range)
        ring_nodes = [f"MULE_{r:03d}_{i}" for i in range(ring_size)]
        fraud_accounts.update(ring_nodes)

        base_amount = rng.uniform(9000, 9999)
        for i in range(ring_size):
            src = ring_nodes[i]
            dst = ring_nodes[(i + 1) % ring_size]
            amount = round(base_amount * rng.uniform(0.95, 0.99), 2)
            G.add_edge(src, dst, amount=amount, is_synthetic_ring=True)

    return fraud_accounts


def detect_cycles_3_to_6(G: nx.DiGraph, max_cycles_scanned: int = 200_000) -> set:
    """
    Mirrors the Cypher rule `(a)-[:TRANSFERRED*3..6]->(a)` used in
    topology_agent.detect_micro_layering_cycles: any account that sits
    on an elementary directed cycle of length 3 to 6 is flagged.

    Uses nx.simple_cycles with a length cap so this stays tractable on
    dense clean graphs (Cypher's variable-length match has the same
    practical need for a bound in production, which is why the real
    query also caps at 6).
    """
    flagged = set()
    scanned = 0
    for cycle in nx.simple_cycles(G, length_bound=6):
        scanned += 1
        if scanned > max_cycles_scanned:
            break
        if 3 <= len(cycle) <= 6:
            flagged.update(cycle)
    return flagged


def run_trial(
    trial_idx: int,
    num_clean_accounts: int,
    avg_out_degree: float,
    num_fraud_rings: int,
    ring_size_range: tuple,
    seed: int,
) -> EvalResult:
    G = build_clean_graph(num_clean_accounts, avg_out_degree, seed=seed)
    fraud_accounts = inject_fraud_rings(G, num_fraud_rings, ring_size_range, seed=seed)

    all_accounts = set(G.nodes)
    clean_accounts = all_accounts - fraud_accounts

    predicted_positive = detect_cycles_3_to_6(G)

    tp = len(predicted_positive & fraud_accounts)
    fp = len(predicted_positive & clean_accounts)
    fn = len(fraud_accounts - predicted_positive)
    tn = len(clean_accounts - predicted_positive)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return EvalResult(
        trial=trial_idx,
        total_accounts=len(all_accounts),
        fraud_accounts=len(fraud_accounts),
        clean_accounts=len(clean_accounts),
        predicted_positive=len(predicted_positive),
        true_positive=tp,
        false_positive=fp,
        false_negative=fn,
        true_negative=tn,
        precision=precision,
        recall=recall,
        false_positive_rate=fpr,
        f1=f1,
    )


def summarize(results: list) -> dict:
    def avg(key):
        return statistics.mean(getattr(r, key) for r in results)

    def stdev(key):
        vals = [getattr(r, key) for r in results]
        return statistics.stdev(vals) if len(vals) > 1 else 0.0

    return {
        "trials": len(results),
        "precision_mean": avg("precision"),
        "precision_std": stdev("precision"),
        "recall_mean": avg("recall"),
        "recall_std": stdev("recall"),
        "fpr_mean": avg("false_positive_rate"),
        "fpr_std": stdev("false_positive_rate"),
        "f1_mean": avg("f1"),
        "f1_std": stdev("f1"),
    }


def print_report(results: list, params: dict):
    summary = summarize(results)
    print("=" * 72)
    print("FraudNet-Zero — Ring Detection Evaluation")
    print("=" * 72)
    print(f"Config: {params}")
    print("-" * 72)
    print(f"{'Trial':<6}{'Accts':<8}{'Fraud':<7}{'PredPos':<9}{'TP':<5}{'FP':<5}{'FN':<5}"
          f"{'Prec':<8}{'Recall':<8}{'FPR':<8}{'F1':<8}")
    for r in results:
        print(f"{r.trial:<6}{r.total_accounts:<8}{r.fraud_accounts:<7}{r.predicted_positive:<9}"
              f"{r.true_positive:<5}{r.false_positive:<5}{r.false_negative:<5}"
              f"{r.precision:<8.3f}{r.recall:<8.3f}{r.false_positive_rate:<8.4f}{r.f1:<8.3f}")
    print("-" * 72)
    print(f"Mean Precision : {summary['precision_mean']:.3f} (± {summary['precision_std']:.3f})")
    print(f"Mean Recall    : {summary['recall_mean']:.3f} (± {summary['recall_std']:.3f})")
    print(f"Mean FPR       : {summary['fpr_mean']:.4f} (± {summary['fpr_std']:.4f})")
    print(f"Mean F1        : {summary['f1_mean']:.3f} (± {summary['f1_std']:.3f})")
    print("=" * 72)
    return summary


# ---------------------------------------------------------------------------
# OPTIONAL: validate against a live Memgraph instance running your actual
# app code, using the exact same ground-truth injection as above. Only run
# this if Memgraph is up and you're OK writing test data into it (use a
# scratch database, not production).
# ---------------------------------------------------------------------------
def verify_against_memgraph(fraud_accounts: set, G: nx.DiGraph):
    """
    Pushes the same synthetic graph into Memgraph and runs your actual
    detect_micro_layering_cycles() from topology_agent.py, so you can
    confirm the offline NetworkX numbers above match production behavior.
    Requires: gqlalchemy, a running Memgraph on 127.0.0.1:7687, and
    gcn_core/topology_agent.py importable on the path.
    """
    from gqlalchemy import Memgraph
    from gcn_core.topology_agent import detect_micro_layering_cycles

    memgraph = Memgraph(host="127.0.0.1", port=7687)
    memgraph.execute("MATCH (n) DETACH DELETE n;")  # scratch DB only

    for u, v, data in G.edges(data=True):
        memgraph.execute(
            "MERGE (a:Account {id: $u}) MERGE (b:Account {id: $v}) "
            "CREATE (a)-[:TRANSFERRED {amount: $amount}]->(b)",
            {"u": u, "v": v, "amount": data.get("amount", 0.0)},
        )

    cycles = detect_micro_layering_cycles()
    detected_accounts = set()
    for c in cycles:
        detected_accounts.update(c["node_ids"])

    tp = len(detected_accounts & fraud_accounts)
    print(f"[Memgraph verification] Fraud accounts detected: {tp}/{len(fraud_accounts)}")
    return detected_accounts


if __name__ == "__main__":
    PARAMS = dict(
        num_clean_accounts=500,
        avg_out_degree=2.0,
        num_fraud_rings=15,
        ring_size_range=(3, 6),
    )
    NUM_TRIALS = 5

    all_results = [
        run_trial(t, seed=1000 + t, **PARAMS)
        for t in range(1, NUM_TRIALS + 1)
    ]

    print_report(all_results, PARAMS)