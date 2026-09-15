# FraudNet-Zero

**Real-Time Graph-Based Fraud Detection & Surgical Containment System**

FraudNet-Zero is an end-to-end fraud detection and response platform that combines real-time graph analytics, explainable machine learning, and network flow theory to detect money laundering rings and surgically contain fraudulent fund flows — without freezing clean user accounts.

---

## Key Features

- **Real-Time Smurfing Detection**
  Identifies multi-hop transaction loops and smurfing rings (3-to-6-node cycles) using in-memory graph traversals over a live Memgraph instance.

- **Explainable Risk Scoring**
  Computes transaction risk probabilities using an XGBoost classifier paired with SHAP attributions to highlight exact fraud drivers.

- **Surgical Mathematical Containment**
  Applies the Max-Flow Min-Cut Theorem on transaction subgraphs to sever minimal cut-edges, reducing fraudulent fund flows to mathematically zero — without freezing clean user accounts.

- **Automated Compliance Reporting**
  Synthesizes isolated fraud metrics and SHAP drivers via the Google Gemini API to generate Suspicious Activity Reports (SAR), with a deterministic local fallback on API failure.

- **Live Visual Operations**
  Streams real-time graph updates, risk scores, and containment events over WebSockets, with a Streamlit dashboard for live inspection.

---

## Results

The 3-to-6-node cycle detection rule was benchmarked on a labeled synthetic dataset (500 accounts, 15 injected fraud rings, 5 trials — see `benchmarks/eval_fraudnet.py`):

| Metric | Value |
|---|---|
| Recall | 100% (± 0.000) |
| Precision | 44.9% (± 1.4%) |
| False Positive Rate | 17.3% (± 1.2%) |
| F1 | 0.620 (± 0.013) |

Recall is structurally guaranteed by the detection rule (injected rings are constructed as cycles). Precision is the meaningful result: on this benchmark, roughly half of flagged accounts are false positives from incidental cycles in the clean transaction graph — this is the direct motivation for the downstream XGBoost + SHAP risk-scoring layer, which filters flagged accounts further before any containment action is taken.

Reproduce with:
```bash
python benchmarks/eval_fraudnet.py
```

---

## System Architecture

FraudNet-Zero operates as a multi-agent pipeline:

1. **Topology Agent** (`gcn_core/topology_agent.py`) — Memgraph-backed cycle detection (3-to-6-node rings), Louvain-style community clustering, and subgraph extraction for containment.
2. **Risk Agent** (`agents/risk_agent.py`) — XGBoost-based risk scoring fused with graph-topology features, explained via SHAP TreeExplainer.
3. **Containment Agent** (`agents/containment_agent.py`) — Builds risk-weighted flow graphs and computes Max-Flow Min-Cut (NetworkX / Edmonds-Karp) to identify the minimal edge set to sever.
4. **Compliance Agent** (`agents/llm_agent.py`) — Packages cut-edge data, risk scores, and SHAP drivers into a prompt processed by the Gemini API to generate SAR documentation, with a local fallback.
5. **Streaming Layer** (`streaming/`) — Kafka producer/consumer ingesting transactions (synthetic + PaySim-derived) into Memgraph, and a WebSocket connection manager broadcasting live events to the dashboard.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Graph Database | Memgraph |
| Streaming / Ingestion | Kafka (confluent-kafka) |
| ML / Risk Scoring | XGBoost, SHAP |
| Flow Optimization | NetworkX (Max-Flow Min-Cut / Edmonds-Karp) |
| Compliance / SAR Generation | Google Gemini API |
| Backend API | FastAPI, WebSockets |
| Dashboard | Streamlit |
| Auth | JWT (role-based: Admin / Analyst) |

---

## Getting Started

### Prerequisites
- Docker (for Memgraph and Kafka via `docker-compose.yml`)
- Python 3.10+
- Google Gemini API key

### Installation
```bash
git clone https://github.com/chopradisha86/fraudnet-zero.git
cd fraudnet-zero
pip install -r requirements.txt
docker-compose up -d
```

### Configuration
Create a `.env` file (never commit this — see `.env.example`):
```
GEMINI_API_KEY=your_api_key_here
FRONTEND_ORIGINS=http://localhost:3000
```

### Running
```bash
python main.py          # FastAPI backend + WebSocket server
streamlit run app.py    # Dashboard
```

---

## Project Structure
```
fraudnet-zero/
├── agents/              # risk_agent.py, containment_agent.py, llm_agent.py
├── gcn_core/             # topology_agent.py — cycle detection & subgraph extraction
├── streaming/            # Kafka producer/consumer, WebSocket connection manager
├── benchmarks/           # eval_fraudnet.py — detection accuracy evaluation
├── query_modules/        # Memgraph query modules
├── reports/              # Generated SAR reports (.md)
├── main.py               # FastAPI application entrypoint
├── app.py                # Streamlit dashboard
├── auth.py                # JWT auth & role-based access control
├── database.py            # SQLite user store
├── docker-compose.yml      # Memgraph + Kafka services
└── README.md
```

---

## Disclaimer
FraudNet-Zero is a decision-support and containment automation prototype built for independent research and portfolio purposes. Detection thresholds, benchmark results, and generated SAR documents have not been validated against real financial data and should not be used for actual regulatory or compliance decisions without expert review.

---

## License
MIT
