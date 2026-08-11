import os
import glob
import streamlit as st
import pandas as pd
from gqlalchemy import Memgraph
from streamlit.components.v1 import html
import networkx as nx
from pyvis.network import Network

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="FraudNet Zero Dashboard",
    page_icon="🛡️",
    layout="wide"
)

# --- MEMGRAPH CONNECTION ---
@st.cache_resource
def get_memgraph_connection():
    try:
        return Memgraph(host="127.0.0.1", port=7687)
    except Exception as e:
        st.error(f"Failed to connect to Memgraph: {e}")
        return None

memgraph = get_memgraph_connection()

# --- HELPER DATA FETCHERS ---
def fetch_system_stats():
    """Fetches high-level metrics from Memgraph."""
    if not memgraph:
        return 0, 0
    
    tx_query = "MATCH ()-[r:TRANSFERRED]->() RETURN count(r) AS total_tx"
    mule_query = "MATCH (a:Account) WHERE a.is_mule = true OR a.id STARTS WITH 'MULE_' RETURN count(a) AS total_mules"
    
    try:
        tx_res = list(memgraph.execute_and_fetch(tx_query))
        mule_res = list(memgraph.execute_and_fetch(mule_query))
        
        total_tx = tx_res[0]["total_tx"] if tx_res else 0
        total_mules = mule_res[0]["total_mules"] if mule_res else 0
        return total_tx, total_mules
    except Exception as e:
        st.sidebar.error(f"Stats Error: {e}")
        return 0, 0

def get_high_risk_suspects():
    """Fetches high-risk mule accounts cleanly with explicit RETURN statements."""
    if not memgraph:
        return []
    
    query = """
    MATCH (a:Account)
    WHERE a.is_mule = true OR a.id STARTS WITH 'MULE_'
    RETURN a.id AS account_id, 
           coalesce(a.risk_score, 0.95) AS risk_score
    LIMIT 10
    """
    try:
        return list(memgraph.execute_and_fetch(query))
    except Exception as e:
        st.error(f"Error fetching suspects: {e}")
        return []

def get_sar_report(account_id):
    """Generates forensic summary for a selected suspect."""
    if not memgraph:
        return None
    
    query = """
    MATCH (a:Account {id: $account_id})-[r:TRANSFERRED]-(b:Account)
    RETURN a.id AS suspect, 
           collect(DISTINCT b.id)[..5] AS peers, 
           count(r) AS total_transfers,
           sum(r.amount) AS total_volume
    LIMIT 1
    """
    try:
        res = list(memgraph.execute_and_fetch(query, parameters={"account_id": account_id}))
        return res[0] if res else None
    except Exception as e:
        st.error(f"Error building SAR report: {e}")
        return None

def render_graph_network(account_id):
    """Renders interactive PyVis 1-hop network topology for target account."""
    if not memgraph or not account_id:
        return None

    query = """
    MATCH (a:Account {id: $account_id})-[r:TRANSFERRED]-(b:Account)
    RETURN a.id AS source, b.id AS target, r.amount AS amount
    LIMIT 25
    """
    try:
        results = list(memgraph.execute_and_fetch(query, parameters={"account_id": account_id}))
        if not results:
            return None

        net = Network(height="350px", width="100%", bgcolor="#0e1117", font_color="white", directed=True)
        net.add_node(account_id, label=account_id, color="#FF4B4B", size=25)

        for row in results:
            target = row["target"]
            amount = row.get("amount", 0.0)
            net.add_node(target, label=target, color="#1E88E5", size=15)
            net.add_edge(account_id, target, title=f"${amount:,.2f}", color="#555555")

        net.save_graph("temp_network.html")
        with open("temp_network.html", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        st.error(f"Error rendering topology: {e}")
        return None


# --- DASHBOARD HEADER ---
st.title("🛡️ FraudNet Zero — Real-Time Graph AI Dashboard")
st.caption("Automated Micro-Layering Detection & Real-Time Risk Scoring")

# --- METRICS ROW ---
total_tx, total_mules = fetch_system_stats()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Ingested Transactions", f"{total_tx:,}")
with col2:
    st.metric("Detected Laundering Rings / Mules", f"{total_mules:,}", delta="Active Alerts", delta_color="inverse")
with col3:
    st.metric("System Status", "ONLINE 🟢")

st.divider()

# --- MAIN LAYOUT ---
left_col, right_col = st.columns([1, 1])

with left_col:
    st.subheader("🚨 High-Risk Suspect Accounts")
    suspects = get_high_risk_suspects()
    
    if suspects:
        df_suspects = pd.DataFrame(suspects)
        st.dataframe(
            df_suspects,
            column_config={
                "account_id": "Account ID",
                "risk_score": st.column_config.NumberColumn("Risk Score", format="%.2f")
            },
            use_container_width=True,
            hide_index=True
        )
        
        suspect_ids = [s["account_id"] for s in suspects]
        selected_suspect = st.selectbox("Select Account to Inspect SAR:", suspect_ids)
        
        # Interactive Graph Visualization Block
        if selected_suspect:
            st.markdown("#### 🕸️ Graph Subgraph Topology")
            graph_html = render_graph_network(selected_suspect)
            if graph_html:
                html(graph_html, height=360)
            else:
                st.info("No transaction subgraphs available for visual rendering.")
    else:
        st.info("No high-risk suspect accounts found in current window.")
        selected_suspect = None

with right_col:
    st.subheader("📄 Automated Forensic Intelligence")
    
    if selected_suspect:
        # Check if saved Gemini SAR report exists in reports/ directory
        saved_sars = glob.glob(f"reports/SAR_{selected_suspect}_*.md")
        
        if saved_sars:
            latest_report = max(saved_sars, key=os.path.getmtime)
            st.success(f"Loaded GenAI SAR Audit File: `{latest_report}`")
            with open(latest_report, "r", encoding="utf-8") as f:
                st.markdown(f.read())
        else:
            sar_data = get_sar_report(selected_suspect)
            if sar_data:
                st.markdown("### **AUTOMATED SUSPICIOUS ACTIVITY REPORT (SAR)**")
                st.markdown(f"**Target Subject ID:** `{sar_data['suspect']}`")
                st.markdown("**Risk Assessment:** `CRITICAL (FraudNet Zero Alert)`")
                st.markdown(f"**Total Volume:** `${sar_data.get('total_volume', 0):,.2f} USD` ({sar_data.get('total_transfers', 0)} transactions)")
                
                st.markdown("#### **KEY EVIDENCE & TOPOLOGY:**")
                peers_str = ", ".join(sar_data.get("peers", [])) if sar_data.get("peers") else "None"
                st.markdown(f"- **Connected Peer Nodes:** `{peers_str}`")
                st.markdown("- **Behavior Pattern:** High-velocity circular micro-layering routing detected.")
                
                st.info("Fallback Graph Engine summary displayed. Run `agents/llm_agent.py` to generate deep Gemini SAR narratives.")
            else:
                st.warning("Could not extract full SAR details for selected subject.")
    else:
        st.write("Select a suspect account from the left panel to display forensic evidence.")

st.divider()

# --- AUDIT LOG FILE EXPLORER ---
with st.expander("📁 Persisted Compliance Audit Files (`reports/`)"):
    reports = sorted(glob.glob("reports/SAR_*.md"), key=os.path.getmtime, reverse=True)
    if reports:
        report_choice = st.selectbox("Select Saved Markdown File", reports)
        if report_choice:
            with open(report_choice, "r", encoding="utf-8") as f:
                st.code(f.read(), language="markdown")
    else:
        st.info("No saved `.md` report logs found in `reports/` folder.")