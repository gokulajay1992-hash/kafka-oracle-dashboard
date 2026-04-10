"""
Kafka → XML→JSON → Oracle  |  Streamlit Dashboard
Run with:  streamlit run app.py
"""

import pandas as pd
import streamlit as st

from config import KAFKA_CONFIG, ORACLE_CONFIG
from db_handler import test_connection
from pipeline import state as consumer_state, test_kafka_connection

# ---------------------------------------------------------------------------
# Page setup  (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Kafka → Oracle Pipeline",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — level badges
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .badge-SUCCESS  { color:#fff; background:#28a745; padding:2px 8px; border-radius:4px; font-size:0.78rem; }
    .badge-INFO     { color:#fff; background:#17a2b8; padding:2px 8px; border-radius:4px; font-size:0.78rem; }
    .badge-ERROR    { color:#fff; background:#dc3545; padding:2px 8px; border-radius:4px; font-size:0.78rem; }
    .badge-WARNING  { color:#212529; background:#ffc107; padding:2px 8px; border-radius:4px; font-size:0.78rem; }
    div[data-testid="metric-container"] { background:#f8f9fa; border-radius:8px; padding:12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar — config summary + controls
# (rendered once, stays interactive — never re-blocked by fragment reruns)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("⚙️ Configuration")

    with st.expander("Kafka", expanded=True):
        st.code(
            f"Broker : {KAFKA_CONFIG['bootstrap_servers']}\n"
            f"Topic  : {KAFKA_CONFIG['topic']}\n"
            f"Group  : {KAFKA_CONFIG['group_id']}\n"
            f"Offset : {KAFKA_CONFIG['auto_offset_reset']}",
            language="text",
        )

    with st.expander("Oracle DB", expanded=True):
        st.code(
            f"Host   : {ORACLE_CONFIG['host']}:{ORACLE_CONFIG['port']}\n"
            f"Service: {ORACLE_CONFIG['service_name']}\n"
            f"Table  : {ORACLE_CONFIG['table_name']}\n"
            f"Ref col: {ORACLE_CONFIG['reference_id_column']}\n"
            f"JSON col: {ORACLE_CONFIG['json_data_column']}",
            language="text",
        )

    st.divider()

    # --- Connection tests ---
    if st.button("🔌 Test Oracle Connection", use_container_width=True):
        ok, msg = test_connection()
        if ok:
            st.success(msg)
        else:
            st.error(msg)

    if st.button("📡 Test Kafka Connection", use_container_width=True):
        with st.spinner("Connecting to Kafka..."):
            ok, msg = test_kafka_connection()
        if ok:
            st.success(msg)
        else:
            st.error(msg)

    st.divider()

    # --- Consumer controls ---
    st.subheader("🎛️ Consumer Controls")

    col_start, col_stop = st.columns(2)
    with col_start:
        if st.button("▶ Start", use_container_width=True, type="primary"):
            if not consumer_state.running:
                consumer_state.start()
            else:
                st.toast("Consumer is already running.", icon="ℹ️")

    with col_stop:
        if st.button("⏹ Stop", use_container_width=True):
            consumer_state.stop()

    if st.button("🗑️ Reset Counters", use_container_width=True):
        consumer_state.reset_counters()

# ---------------------------------------------------------------------------
# Page header  (static — rendered once, never refreshed)
# ---------------------------------------------------------------------------
st.title("📊 Kafka → Oracle Pipeline Dashboard")
st.caption("Real-time XML message ingestion and Oracle DB update tracker")

# ---------------------------------------------------------------------------
# Live dashboard fragment
# ---------------------------------------------------------------------------
# @st.fragment(run_every=1) tells Streamlit to re-execute ONLY this function
# every 1 second — the rest of the page (sidebar, title) is untouched.
# This eliminates the sleep+rerun hack and prevents full-page flicker.
# Requires Streamlit >= 1.37
# ---------------------------------------------------------------------------
@st.fragment(run_every=1)
def live_dashboard():
    snap = consumer_state.snapshot()

    # --- Status banner ---
    if snap["running"]:
        st.success("🟢  Consumer is **running** and listening for messages.", icon="✅")
    else:
        st.warning("🔴  Consumer is **stopped**. Use the sidebar to start it.", icon="⚠️")

    st.divider()

    # ── Metrics row ──────────────────────────────────────────────────────────
    total = snap["processed"] + snap["failed"]
    success_rate = (snap["processed"] / total * 100) if total > 0 else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        label="✅  Processed",
        value=snap["processed"],
        help="Messages successfully converted and saved to Oracle.",
    )
    m2.metric(
        label="❌  Failed",
        value=snap["failed"],
        help="Messages that could not be parsed or saved.",
    )
    m3.metric(
        label="📨  Total Received",
        value=total,
        help="Total messages consumed from Kafka.",
    )
    m4.metric(
        label="📈  Success Rate",
        value=f"{success_rate:.1f}%",
        help="Processed / Total × 100",
    )

    st.divider()

    # ── Throughput chart ─────────────────────────────────────────────────────
    timeline = snap["timeline"]
    if len(timeline) >= 2:
        st.subheader("📉 Processing Timeline")
        df_tl = pd.DataFrame(timeline).set_index("ts")
        st.line_chart(df_tl[["processed", "failed"]], height=200, use_container_width=True)
        st.divider()

    # ── Log table ────────────────────────────────────────────────────────────
    st.subheader("📋 Message Logs")

    logs = snap["logs"]  # already newest-first

    if not logs:
        st.info("No messages yet. Start the consumer to begin processing.")
        return

    # Filter controls
    f1, f2, f3 = st.columns([2, 2, 1])
    with f1:
        filter_level = st.multiselect(
            "Filter by Level",
            options=["SUCCESS", "INFO", "ERROR", "WARNING"],
            default=["SUCCESS", "INFO", "ERROR", "WARNING"],
        )
    with f2:
        filter_ref = st.text_input("Filter by Reference ID", placeholder="leave blank for all")
    with f3:
        max_rows = st.number_input("Max rows shown", min_value=10, max_value=500, value=100, step=10)

    df = pd.DataFrame(logs)

    if filter_level:
        df = df[df["level"].isin(filter_level)]
    if filter_ref.strip():
        df = df[df["reference_id"].str.contains(filter_ref.strip(), case=False, na=False)]

    df = df.head(max_rows).reset_index(drop=True)

    if df.empty:
        st.info("No log entries match the current filter.")
        return

    def _badge(level: str) -> str:
        return f'<span class="badge-{level}">{level}</span>'

    df_display = df.copy()
    df_display["level"] = df_display["level"].apply(_badge)
    st.write(
        df_display.to_html(escape=False, index=False),
        unsafe_allow_html=True,
    )


# Render the live fragment (Streamlit handles the 1s re-execution automatically)
live_dashboard()
