# FraudNet-Zero

**Real-Time Graph-Based Fraud Detection & Surgical Containment System**

FraudNet-Zero is an end-to-end fraud detection and response platform that combines real-time graph analytics, explainable machine learning, and network flow theory to detect money laundering rings and surgically contain fraudulent fund flows — without freezing clean user accounts.

---

## Key Features

- **Real-Time Smurfing Detection**
  Identifies multi-hop transaction loops and smurfing rings (3 to 6-node cycles) within sub-15ms latencies using in-memory graph traversals.

- **Explainable Risk Scoring**
  Computes sub-5ms transaction risk probabilities using an XGBoost classifier paired with SHAP attributions to highlight exact fraud drivers.

- **Surgical Mathematical Containment**
  Applies the Max-Flow Min-Cut Theorem on transaction subgraphs to sever minimal cut-edges, reducing fraudulent fund flows to mathematically zero — without freezing clean user accounts.

- **Automated Compliance Reporting**
  Synthesizes isolated fraud metrics and SHAP drivers via the Google Gemini API to generate instant, standardized Suspicious Activity Reports (SAR).

- **Live Visual Operations**
  Renders real-time dynamic graph updates, red-highlighted cut-edges, and risk analytics on an interactive Cytoscape.js dashboard over WebSockets.

---

## System Architecture

FraudNet-Zero operates as a five-stage pipeline:

1. **Graph Topology & Ring Extraction** — Memgraph-backed multi-graph modeling of transaction networks; variable-length path matching for cycle detection; Louvain community detection for clustering dense fraud communities.
2. **Risk Scoring Engine** — XGBoost-based risk classification fused with topological graph features, explained via SHAP values.
3. **Dynamic Flow Modeling** — Converts flagged subgraphs into capacitated flow networks where edge capacity is inversely weighted by risk score.
4. **Containment Engine** — Runs Edmonds-Karp / Ford-Fulkerson max-flow min-cut to identify and sever the minimal set of edges required to zero out fraudulent flow.
5. **Compliance Agent** — Packages cut-edge data, risk scores, and SHAP drivers into a structured prompt, processed by the Gemini API to auto-generate SAR documentation.

---

## Mathematical Foundation

| Component | Method |
|---|---|
| Ring Extraction | Variable-length cycle detection, `Cycle(a) = {P = (a, v_1, ..., v_{k-1}, a)}` |
| Community Detection | Louvain Modularity Maximization (Q) |
| Risk Scoring | XGBoost ensemble, sigmoid-activated: `R(X_i) = σ(Σ f_m(X_i))` |
| Explainability | SHAP values: `φ_j = Σ_{S⊆F\{j}} [weight] * [f_x(S∪{j}) - f_x(S)]` |
| Edge Capacity | `c(u, v) = B_u / (1 + α·R(u, v))` |
| Containment | Max-Flow Min-Cut Theorem via Edmonds-Karp |
| Reporting | Gemini API structured JSON generation |

> Full derivations and formulas are documented in [`METHODOLOGY.md`](./METHODOLOGY.md).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Graph Database | Memgraph |
| ML / Risk Scoring | XGBoost, SHAP |
| Flow Optimization | Edmonds-Karp (Max-Flow Min-Cut) |
| Compliance / SAR Generation | Google Gemini API |
| Real-Time Dashboard | Cytoscape.js + WebSockets |
| Backend | (specify: e.g., Python / FastAPI / Node.js) |

---

## Getting Started

### Prerequisites
- Memgraph instance running and accessible
- Python 3.10+ (or specify your runtime)
- Google Gemini API key
- Node.js (for the Cytoscape.js dashboard, if applicable)

### Installation
```bash
git clone <repo-url>
cd fraudnet-zero
pip install -r requirements.txt
```

### Configuration
Create a `.env` file with:
```
MEMGRAPH_URI=bolt://localhost:7687
GEMINI_API_KEY=your_api_key_here
WEBSOCKET_PORT=8080
```

### Running
```bash
python main.py
```
Then open the dashboard at `http://localhost:<port>` to view live graph updates and containment actions.

---

## Project Structure
```
fraudnet-zero/
├── graph/              # Memgraph queries, cycle & Louvain clustering logic
├── risk_engine/         # XGBoost model training/inference + SHAP explainability
├── containment/          # Max-flow min-cut engine
├── compliance_agent/     # Gemini API SAR generation
├── dashboard/            # Cytoscape.js + WebSocket frontend
├── METHODOLOGY.md        # Full mathematical documentation
└── README.md
```

---

## Disclaimer
FraudNet-Zero is a decision-support and containment automation system. Generated SAR documents and containment actions should be reviewed by qualified compliance personnel before regulatory submission or account-level enforcement.

---

## License
Specify your license here (e.g., MIT, Apache 2.0, Proprietary).