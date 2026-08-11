from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
import streamlit as st

# Setup repo root in sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.metrics import percentile

# Page config
st.set_page_config(
    page_title="Day 13 AI Observability Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for rich aesthetics
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .panel-box {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .badge-ok {
        background-color: #DCFCE7;
        color: #166534;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-alert {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Auto refresh every 30 seconds
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30000, limit=None, key="dashboard_autorefresh")
except Exception:
    pass

st.markdown('<div class="main-header">📊 Day 13 AI Observability Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Real-time metrics & log analytics (Time Range: <b>Last 60 Minutes</b> | Refresh: <b>30s</b>)</div>', unsafe_allow_html=True)

# Load log data
LOG_FILE = REPO_ROOT / "data" / "logs.jsonl"

@st.cache_data(ttl=5)
def load_logs(file_path: Path) -> pd.DataFrame:
    if not file_path.exists():
        return pd.DataFrame()
    records = []
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                records.append(data)
            except json.JSONDecodeError:
                continue
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    # Parse timestamp
    ts_col = "ts" if "ts" in df.columns else ("timestamp" if "timestamp" in df.columns else None)
    if ts_col:
        df["dt"] = pd.to_datetime(df[ts_col], errors="coerce", utc=True)
    else:
        df["dt"] = pd.NaT
    return df

raw_df = load_logs(LOG_FILE)

now_utc = datetime.now(timezone.utc)
cutoff_time = now_utc - timedelta(minutes=60)

if not raw_df.empty and "dt" in raw_df.columns:
    df = raw_df[raw_df["dt"] >= cutoff_time].copy()
else:
    df = pd.DataFrame()

# Sidebar summary & control
with st.sidebar:
    st.header("⚙️ Dashboard Controls")
    st.info("🕒 **Time Window**: Last 60 Minutes\n🔄 **Auto-refresh**: 30 seconds")
    if st.button("🔄 Manual Refresh"):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    st.subheader("📌 Log Statistics")
    total_logs = len(df)
    st.metric("Total Records (60m)", total_logs)
    if not df.empty and "event" in df.columns:
        event_counts = df["event"].value_counts().to_dict()
        for evt, count in event_counts.items():
            st.caption(f"• **{evt}**: {count}")

# 6 Panels Display
col1, col2 = st.columns(2)

# Panel 1: Latency (p50, p95, p99)
with col1:
    st.markdown("### 1. Latency Percentiles (`latency`)")
    resp_df = df[df["event"] == "response_sent"] if not df.empty and "event" in df.columns else pd.DataFrame()
    
    if not resp_df.empty and "latency_ms" in resp_df.columns:
        latencies = [int(val) for val in resp_df["latency_ms"].dropna().tolist()]
        p50_val = percentile(latencies, 50)
        p95_val = percentile(latencies, 95)
        p99_val = percentile(latencies, 99)
        
        status_badge = '<span class="badge-ok">PASS (≤ 3000 ms)</span>' if p95_val <= 3000 else '<span class="badge-alert">ALERT (> 3000 ms)</span>'
        st.markdown(f"**Threshold**: p95 ≤ 3000 ms | Status: {status_badge}", unsafe_allow_html=True)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("p50 Latency", f"{p50_val:.1f} ms")
        m2.metric("p95 Latency", f"{p95_val:.1f} ms")
        m3.metric("p99 Latency", f"{p99_val:.1f} ms")
        
        # Time-series chart
        resp_df["minute"] = resp_df["dt"].dt.floor("1min")
        chart_data = resp_df.groupby("minute")["latency_ms"].agg(
            p50=lambda x: percentile([int(v) for v in x], 50),
            p95=lambda x: percentile([int(v) for v in x], 95),
            p99=lambda x: percentile([int(v) for v in x], 99),
        )
        chart_data["threshold_3000ms"] = 3000
        st.line_chart(chart_data)
    else:
        st.warning("Chưa có dữ liệu `response_sent` trong 60 phút qua.")

# Panel 2: Traffic (Request count & rate per minute)
with col2:
    st.markdown("### 2. Request Traffic (`traffic`)")
    req_df = df[df["event"] == "request_received"] if not df.empty and "event" in df.columns else pd.DataFrame()
    
    total_requests = len(req_df)
    rpm = total_requests / 60.0
    
    status_badge = '<span class="badge-ok">PASS (≥ 1 req/min)</span>' if rpm >= 1.0 else '<span class="badge-alert">LOW TRAFFIC (< 1 req/min)</span>'
    st.markdown(f"**Threshold**: rate_per_minute ≥ 1.0 | Status: {status_badge}", unsafe_allow_html=True)
    
    m1, m2 = st.columns(2)
    m1.metric("Total Requests (60m)", f"{total_requests}")
    m2.metric("Rate / Minute", f"{rpm:.2f} req/min")
    
    if not req_df.empty:
        req_df["minute"] = req_df["dt"].dt.floor("1min")
        traffic_data = req_df.groupby("minute").size().to_frame(name="requests_per_minute")
        traffic_data["threshold_1rpm"] = 1.0
        st.line_chart(traffic_data)
    else:
        st.warning("Chưa có dữ liệu `request_received` trong 60 phút qua.")

st.markdown("---")

col3, col4 = st.columns(2)

# Panel 3: Errors (Error rate % & breakdown)
with col3:
    st.markdown("### 3. Error Rate & Breakdown (`errors`)")
    failed_df = df[df["event"] == "request_failed"] if not df.empty and "event" in df.columns else pd.DataFrame()
    total_req_cnt = len(req_df)
    failed_cnt = len(failed_df)
    
    error_rate_pct = (failed_cnt / total_req_cnt * 100.0) if total_req_cnt > 0 else 0.0
    status_badge = '<span class="badge-ok">PASS (≤ 2%)</span>' if error_rate_pct <= 2.0 else '<span class="badge-alert">ALERT (> 2%)</span>'
    st.markdown(f"**Threshold**: error_rate_pct ≤ 2% | Status: {status_badge}", unsafe_allow_html=True)
    
    m1, m2 = st.columns(2)
    m1.metric("Error Rate", f"{error_rate_pct:.2f} %")
    m2.metric("Failed Requests", f"{failed_cnt}")
    
    if not failed_df.empty and "error_type" in failed_df.columns:
        breakdown = failed_df["error_type"].value_counts().to_frame(name="count")
        st.bar_chart(breakdown)
    else:
        st.caption("🟢 Không có lỗi recorded trong cửa sổ này (Error Breakdown rỗng).")

# Panel 4: Cost (Cost over time & total)
with col4:
    st.markdown("### 4. Cost Over Time (`cost`)")
    if not resp_df.empty and "cost_usd" in resp_df.columns:
        total_cost = float(resp_df["cost_usd"].sum())
        status_badge = '<span class="badge-ok">PASS (≤ $2.50)</span>' if total_cost <= 2.50 else '<span class="badge-alert">ALERT (> $2.50)</span>'
        st.markdown(f"**Threshold**: total ≤ $2.50 USD | Status: {status_badge}", unsafe_allow_html=True)
        
        st.metric("Total Window Cost", f"${total_cost:.4f} USD")
        
        resp_df["minute"] = resp_df["dt"].dt.floor("1min")
        cost_by_min = resp_df.groupby("minute")["cost_usd"].sum().to_frame(name="cost_usd_per_min")
        st.line_chart(cost_by_min)
    else:
        st.warning("Chưa có dữ liệu `cost_usd` trong 60 phút qua.")

st.markdown("---")

col5, col6 = st.columns(2)

# Panel 5: Tokens (Input & Output tokens)
with col5:
    st.markdown("### 5. Input & Output Tokens (`tokens`)")
    if not resp_df.empty and "tokens_in" in resp_df.columns and "tokens_out" in resp_df.columns:
        total_in = int(resp_df["tokens_in"].sum())
        total_out = int(resp_df["tokens_out"].sum())
        total_tokens = total_in + total_out
        
        status_badge = '<span class="badge-ok">PASS (≤ 50,000)</span>' if total_tokens <= 50000 else '<span class="badge-alert">ALERT (> 50,000)</span>'
        st.markdown(f"**Threshold**: total_tokens ≤ 50,000 | Status: {status_badge}", unsafe_allow_html=True)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Tokens In", f"{total_in:,}")
        m2.metric("Tokens Out", f"{total_out:,}")
        m3.metric("Total Tokens", f"{total_tokens:,}")
        
        token_df = pd.DataFrame({
            "Token Type": ["tokens_in", "tokens_out"],
            "Count": [total_in, total_out]
        }).set_index("Token Type")
        st.bar_chart(token_df)
    else:
        st.warning("Chưa có dữ liệu `tokens` trong 60 phút qua.")

# Panel 6: Quality (Quality proxy)
with col6:
    st.markdown("### 6. Quality Proxy (`quality`)")
    if not resp_df.empty and "quality_score" in resp_df.columns:
        avg_quality = float(resp_df["quality_score"].mean())
        status_badge = '<span class="badge-ok">PASS (≥ 0.75)</span>' if avg_quality >= 0.75 else '<span class="badge-alert">ALERT (< 0.75)</span>'
        st.markdown(f"**Threshold**: mean quality_score ≥ 0.75 | Status: {status_badge}", unsafe_allow_html=True)
        
        st.metric("Average Quality Score", f"{avg_quality:.3f}")
        
        resp_df["minute"] = resp_df["dt"].dt.floor("1min")
        quality_by_min = resp_df.groupby("minute")["quality_score"].mean().to_frame(name="mean_quality_score")
        quality_by_min["threshold_0.75"] = 0.75
        st.line_chart(quality_by_min)
    else:
        st.warning("Chưa có dữ liệu `quality_score` trong 60 phút qua.")
