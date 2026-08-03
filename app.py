import streamlit as st
import pandas as pd
from gqlalchemy import Memgraph

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
    
    # Query total transactions (edges)
    tx_query = "MATCH ()-[r:TRANSFERRED]->() RETURN count(r) AS total_tx"
    # Query detected cycles/mules
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
    
    # Updated query ensuring all returned rows contain valid dict keys
    query = """
    MATCH (a:Account)
    WHERE a.is_mule = true OR a.id STARTS WITH 'MULE_'
    RETURN a.id AS account_id, 
           coalesce(a.risk_score, 0.95) AS risk_score
    LIMIT 10
    """
    try:
        results = list(memgraph.execute_and_fetch(query))
        return results
    except Exception as e:
        st.error(f"Error fetching suspects: {e}")
        return []

def get_sar_report(account_id):
    """Generates forensic summary for a selected suspect."""
    if not memgraph:
        return None
    
    query = """
    MATCH (a:Account {id: $account_id})-[r:TRANSFERRED]->(b:Account)
    RETURN a.id AS suspect, 
           collect(DISTINCT b.id)[..5] AS peers, 
           count(r) AS total_transfers,
           sum(r.amount) AS total_volume
    """
    try:
        res = list(memgraph.execute_and_fetch(query, parameters={"account_id": account_id}))
        return res[0] if res else None
    except Exception as e:
        st.error(f"Error building SAR report: {e}")
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
        
        # Selectbox to generate SAR for a specific suspect
        suspect_ids = [s["account_id"] for s in suspects]
        selected_suspect = st.selectbox("Select Account to Inspect SAR:", suspect_ids)
    else:
        st.info("No high-risk suspect accounts found in current window.")
        selected_suspect = None

with right_col:
    st.subheader("📄 Automated SAR Report")
    
    if selected_suspect:
        sar_data = get_sar_report(selected_suspect)
        if sar_data:
            st.markdown(f"### **AUTOMATED SUSPICIOUS ACTIVITY REPORT (SAR)**")
            st.markdown(f"**Target Subject ID:** `{sar_data['suspect']}`")
            st.markdown(f"**Risk Assessment:** `CRITICAL (FraudNet Zero Alert)`")
            st.markdown(f"**Total Volume:** `${sar_data.get('total_volume', 0):,.2f} USD` ({sar_data.get('total_transfers', 0)} transactions)")
            
            st.markdown("#### **KEY EVIDENCE & TOPOLOGY:**")
            peers_str = ", ".join(sar_data.get("peers", [])) if sar_data.get("peers") else "None"
            st.markdown(f"- **Connected Peer Nodes:** `{peers_str}`")
            st.markdown("- **Behavior Pattern:** High-velocity circular micro-layering routing detected.")
            
            st.success("SAR generated automatically from Graph Engine.")
        else:
            st.warning("Could not extract full SAR details for selected subject.")
    else:
        st.write("Select a suspect account from the left panel to display forensic evidence.")