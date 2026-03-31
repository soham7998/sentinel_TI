"""
SentinelTI – SOC Dashboard (Streamlit)
Tabs:
  1. 📡 Live Feed        – real-time IOC table with risk colouring
  2. 🧠 ML Risk Scoring  – risk distribution, score histogram
  3. 🔍 SHAP Global      – global feature importance bar chart
  4. 🔎 SHAP Local       – per-IP waterfall explanation
  5. 📊 Analytics        – top countries, top sources, enrichment coverage
"""

import os
import time
import requests
import pandas as pd
import streamlit as st

BACKEND = os.getenv("BACKEND_URL", "http://backend:8000")

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SentinelTI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .risk-high   { background:#c62828; color:#fff; padding:4px 10px; border-radius:6px; font-weight:700; }
  .risk-medium { background:#f57c00; color:#fff; padding:4px 10px; border-radius:6px; font-weight:700; }
  .risk-low    { background:#2e7d32; color:#fff; padding:4px 10px; border-radius:6px; font-weight:700; }
  .metric-card { background:#1e1e2e; border-radius:10px; padding:16px; text-align:center; }
  .metric-val  { font-size:2.2rem; font-weight:800; }
  .metric-lbl  { font-size:0.85rem; color:#aaa; margin-top:4px; }
  .stDataFrame { font-size:0.82rem; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ────────────────────────────────────────────────────────────────────

def api(path: str, method="GET", **kwargs):
    try:
        fn  = requests.post if method == "POST" else requests.get
        r   = fn(f"{BACKEND}{path}", timeout=8, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Backend error: {e}")
        return None


def risk_badge(risk: str) -> str:
    cls = {"HIGH": "risk-high", "MEDIUM": "risk-medium", "LOW": "risk-low"}.get(risk, "risk-low")
    return f'<span class="{cls}">{risk}</span>'


def color_row(row):
    colors = {
        "HIGH":   "background-color:#5c1a1a; color:#fff",
        "MEDIUM": "background-color:#4a3000; color:#fff",
        "LOW":    "",
    }
    c = colors.get(row.get("ml_risk") or row.get("risk", ""), "")
    return [c] * len(row)


def load_indicators() -> pd.DataFrame:
    data = api("/indicators?limit=200")
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if df.empty:
        return df

    # Normalise sources list → string
    if "sources" in df.columns:
        df["sources"] = df["sources"].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else str(x or "")
        )

    # Datetime columns
    for col in ("first_seen", "last_seen", "last_abuse_time"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Use ML risk if available, else feed-level risk
    if "ml_risk" not in df.columns:
        df["ml_risk"] = df.get("risk", "LOW")
    df["ml_risk"] = df["ml_risk"].fillna(df.get("risk", "LOW"))

    if "ml_score" not in df.columns:
        df["ml_score"] = None

    return df


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.shields.io/badge/SentinelTI-SOC%20Dashboard-blue?style=for-the-badge", width=240)
    st.markdown("---")

    status = api("/status") or {}
    fetch_running = status.get("fetch_in_progress", False)
    ml_running    = status.get("ml_in_progress", False)

    if fetch_running:
        st.warning("⏳ Fetching & enriching…")
    elif ml_running:
        st.info("🧠 ML scoring in progress…")
    else:
        st.success("✅ System idle")

    st.markdown("---")
    st.markdown("### Actions")

    enrich_limit = st.select_slider(
        "IOC Limit", options=[25, 50, 100, 200], value=50,
        help="25 = ~1 min | 50 = ~2 min | 100 = ~5 min | 200 = ~15 min"
    )

    if st.button("🚀 Fetch Now", disabled=fetch_running, use_container_width=True):
        api(f"/fetch?limit={enrich_limit}", method="POST")
        st.toast(f"Fetching {enrich_limit} IOCs…", icon="⏳")
        time.sleep(1)
        st.rerun()

    # Show enrichment progress bar
    if fetch_running:
        enriched_so_far = status.get("enriched", 0)
        total_so_far    = status.get("total", 1)
        pct = enriched_so_far / max(total_so_far, 1)
        st.progress(pct, text=f"Enriched {enriched_so_far}/{total_so_far}")

    if st.button("🧠 Run ML Scoring", disabled=(fetch_running or ml_running), use_container_width=True):
        enriched_count = status.get("enriched", 0)
        with st.spinner(f"Scoring {enriched_count} enriched IOCs with RF+XGBoost…"):
            result = api("/ml/score", method="POST")
            if result and result.get("status") == "done":
                st.success(f"✅ ML Scoring complete — {result.get('scored', 0)} of {result.get('total', 0)} IOCs scored!")
            elif result:
                st.info(str(result))
        st.rerun()

    if ml_running:
        prog = api("/ml/score/progress") or {}
        scored_n = prog.get("scored", 0)
        total_n  = prog.get("total", 1)
        pct_n    = prog.get("pct", 0)
        st.progress(scored_n / max(total_n, 1),
                    text=f"ML Scoring: {scored_n}/{total_n} ({pct_n}%)")

    st.markdown("---")
    st.markdown("### Summary")
    for label, key, colour in [
        ("Total IOCs",  "total",  "#90caf9"),
        ("HIGH",        "high",   "#ef9a9a"),
        ("MEDIUM",      "medium", "#ffcc80"),
        ("LOW",         "low",    "#a5d6a7"),
        ("Enriched",    "enriched","#ce93d8"),
        ("ML Scored",   "ml_scored","#80deea"),
    ]:
        val = status.get(key, "–")
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;margin:4px 0">'
            f'<span style="color:{colour}">{label}</span>'
            f'<strong>{val}</strong></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    auto_refresh = st.checkbox("🔄 Auto-refresh (2 min)", value=False)


# ── Load Data ──────────────────────────────────────────────────────────────────
df = load_indicators()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📡 Live Feed",
    "🧠 ML Risk Scoring",
    "🔍 SHAP Global",
    "🔎 SHAP Local",
    "📊 Analytics",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 – Live Feed
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("## 📡 Recent Indicators of Compromise")

    if df.empty:
        st.info("No indicators yet. Click **Fetch Now** in the sidebar.")
    else:
        # Live enrichment banner
        if fetch_running:
            enriched_n = int(df["enriched"].eq(True).sum()) if "enriched" in df.columns else 0
            st.info(f"⏳ Enrichment running… {enriched_n}/{len(df)} enriched so far. Refreshing every 5s.")

        # Human-readable status column
        if "enriched" in df.columns:
            df["status"] = df["enriched"].apply(
                lambda x: "✅ Enriched" if x is True else "⏳ Pending"
            )

        # Filter bar
        col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
        with col_f1:
            risk_filter = st.multiselect(
                "Risk Level", ["HIGH", "MEDIUM", "LOW"],
                default=["HIGH", "MEDIUM", "LOW"]
            )
        with col_f2:
            enriched_filter = st.selectbox("Enrichment", ["All", "Enriched", "Pending"])
        with col_f3:
            search = st.text_input("🔍 Search IP", placeholder="e.g. 185.220")

        fdf = df[df["ml_risk"].isin(risk_filter)].copy()
        if enriched_filter == "Enriched" and "enriched" in fdf.columns:
            fdf = fdf[fdf["enriched"] == True]
        elif enriched_filter == "Pending" and "enriched" in fdf.columns:
            fdf = fdf[fdf["enriched"] != True]
        if search:
            fdf = fdf[fdf["indicator"].str.contains(search, na=False)]

        # Show available columns (more appear as enrichment completes)
        show_cols = [c for c in [
            "indicator", "status", "ml_risk", "ml_score",
            "sources", "score", "confidence_score", "abuse_reports",
            "country", "city", "isp", "first_seen", "last_seen",
        ] if c in fdf.columns]

        st.dataframe(
            fdf[show_cols].style.apply(color_row, axis=1),
            use_container_width=True,
            height=500,
        )
        st.caption(f"Showing {len(fdf)} of {len(df)} indicators")

        # Fast refresh while enrichment is running
        if fetch_running:
            time.sleep(5)
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 – ML Risk Scoring
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("## 🧠 ML Risk Score Distribution")

    if df.empty or "ml_score" not in df.columns or df["ml_score"].isna().all():
        st.info("No ML scores yet. Click **Run ML Scoring** in the sidebar after fetching.")
    else:
        scored_df = df[df["ml_score"].notna()].copy()

        # Top metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Scored",   len(scored_df))
        c2.metric("HIGH Risk",      int((scored_df["ml_risk"] == "HIGH").sum()),   delta_color="inverse")
        c3.metric("MEDIUM Risk",    int((scored_df["ml_risk"] == "MEDIUM").sum()))
        c4.metric("LOW Risk",       int((scored_df["ml_risk"] == "LOW").sum()),    delta_color="normal")

        st.markdown("---")
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("### Risk Score Distribution")
            hist_data = scored_df["ml_score"].dropna()
            # Build histogram manually for Streamlit
            import numpy as np
            counts, edges = np.histogram(hist_data, bins=20, range=(0, 1))
            bin_labels = [f"{edges[i]:.2f}" for i in range(len(edges) - 1)]
            hist_df = pd.DataFrame({"Score Range": bin_labels, "Count": counts})
            st.bar_chart(hist_df.set_index("Score Range"))

        with col_b:
            st.markdown("### Risk Level Breakdown")
            risk_counts = scored_df["ml_risk"].value_counts().reset_index()
            risk_counts.columns = ["Risk Level", "Count"]
            st.bar_chart(risk_counts.set_index("Risk Level"))

        st.markdown("---")
        st.markdown("### 🔴 Top HIGH Risk IPs")
        high_df = scored_df[scored_df["ml_risk"] == "HIGH"].sort_values(
            "ml_score", ascending=False
        ).head(20)

        show_ml_cols = [c for c in [
            "indicator", "ml_score", "rf_prob", "xgb_prob",
            "sources", "confidence_score", "abuse_reports",
            "country", "isp"
        ] if c in high_df.columns]

        if not high_df.empty:
            st.dataframe(
                high_df[show_ml_cols].style.apply(color_row, axis=1),
                use_container_width=True,
            )
        else:
            st.info("No HIGH risk IPs yet.")

        st.markdown("### 🟡 Top MEDIUM Risk IPs")
        med_df = scored_df[scored_df["ml_risk"] == "MEDIUM"].sort_values(
            "ml_score", ascending=False
        ).head(10)
        if not med_df.empty:
            st.dataframe(med_df[show_ml_cols], use_container_width=True)
        else:
            st.info("No MEDIUM risk IPs.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 – SHAP Global
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("## 🔍 Global SHAP – Feature Importance")
    st.markdown(
        "Shows which features contribute most to malicious IP predictions "
        "across all indicators (mean |SHAP value|)."
    )

    if st.button("📊 Load Global SHAP"):
        with st.spinner("Computing SHAP values…"):
            result = api("/ml/shap/global")

        if result and "global_shap" in result:
            shap_df = pd.DataFrame(result["global_shap"])
            shap_df = shap_df.sort_values("importance", ascending=True)

            st.markdown("### Feature Importance (Mean |SHAP|)")
            # Horizontal bar chart
            st.bar_chart(
                shap_df.set_index("feature")["importance"],
                horizontal=True,
                height=400,
            )

            st.markdown("### Detailed Breakdown")
            display_df = shap_df.sort_values("importance", ascending=False).copy()
            display_df["importance"] = display_df["importance"].round(5)
            display_df["pct"] = display_df["pct"].apply(lambda x: f"{x:.1f}%")
            display_df.columns = ["Feature", "Mean |SHAP|", "% Contribution"]
            st.dataframe(display_df, use_container_width=True)

            st.markdown("""
            **Feature key:**
            | Feature | Description |
            |---|---|
            | `confidence_pct` | AbuseIPDB confidence score (0-100) |
            | `abuse_reports` | Number of historical abuse reports |
            | `vt_detections` | VirusTotal malicious vendor count |
            | `recency_hrs` | Hours since last abuse report |
            | `freshness` | Inverse of recency (1=very fresh threat) |
            | `geo_risk` | IP from high-risk country |
            | `multi_source` | Flagged by >1 feed/enrichment source |
            | `attack_type_count` | Distinct attack categories |
            | `source_score` | Normalised feed-level risk score |
            | `vt_total` | Total VirusTotal vendors checked |
            """)
        elif result and "error" in result:
            st.error(f"SHAP error: {result['error']}")
    else:
        st.info("Click **Load Global SHAP** to compute feature importance across all indicators.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 – SHAP Local
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("## 🔎 Local SHAP – Per-IP Explanation")
    st.markdown(
        "Explains exactly which features pushed a specific IP's risk score "
        "up or down relative to the baseline."
    )

    if df.empty:
        st.info("No indicators loaded yet.")
    else:
        ip_options = df["indicator"].dropna().unique().tolist()
        selected_ip = st.selectbox("Select IP Address", ip_options)

        if st.button("🔍 Explain This IP"):
            with st.spinner(f"Computing SHAP explanation for {selected_ip}…"):
                result = api(f"/ml/shap/local/{selected_ip}")

            if result and "local_shap" in result:
                risk_score = result.get("risk_score", 0)
                base_value = result.get("base_value", 0)

                # Header
                risk_label = "HIGH" if risk_score >= 0.7 else "MEDIUM" if risk_score >= 0.3 else "LOW"
                badge      = risk_badge(risk_label)

                st.markdown(f"""
                <div style="background:#1e1e2e;padding:16px;border-radius:10px;margin-bottom:16px">
                  <h3 style="margin:0">IP: <code>{selected_ip}</code> &nbsp; {badge}</h3>
                  <p style="margin:8px 0 0 0">
                    ML Risk Score: <strong>{risk_score:.4f}</strong> &nbsp;|&nbsp;
                    Baseline: <strong>{base_value:.4f}</strong>
                  </p>
                </div>
                """, unsafe_allow_html=True)

                shap_local_df = pd.DataFrame(result["local_shap"])

                # Waterfall-style bar chart
                st.markdown("### Feature Contributions to Risk Score")
                chart_df = shap_local_df.sort_values("shap_value", ascending=True).copy()

                # Colour positive (red = increases risk) vs negative (green = decreases)
                chart_df["colour_label"] = chart_df["shap_value"].apply(
                    lambda v: "Increases Risk" if v > 0 else "Decreases Risk"
                )

                positive = chart_df[chart_df["shap_value"] > 0].set_index("feature")["shap_value"]
                negative = chart_df[chart_df["shap_value"] < 0].set_index("feature")["shap_value"]

                col_pos, col_neg = st.columns(2)
                with col_pos:
                    st.markdown("🔴 **Increases Risk**")
                    if not positive.empty:
                        st.bar_chart(positive, height=300)
                    else:
                        st.info("No features increased risk")
                with col_neg:
                    st.markdown("🟢 **Decreases Risk**")
                    if not negative.empty:
                        st.bar_chart(negative.abs(), height=300)
                    else:
                        st.info("No features decreased risk")

                # Detailed table
                st.markdown("### Full Explanation Table")
                display_shap = shap_local_df[
                    ["feature", "value", "shap_value", "direction"]
                ].copy()
                display_shap.columns = ["Feature", "Feature Value", "SHAP Value", "Direction"]
                display_shap["SHAP Value"] = display_shap["SHAP Value"].round(5)

                def colour_direction(val):
                    if val == "increases_risk":
                        return "color: #ef9a9a"
                    return "color: #a5d6a7"

                st.dataframe(
                    display_shap.style.applymap(
                        colour_direction, subset=["Direction"]
                    ),
                    use_container_width=True,
                )

                # Also show the raw IOC details
                ip_row = df[df["indicator"] == selected_ip]
                if not ip_row.empty:
                    with st.expander("📋 Raw IOC Details"):
                        st.json(ip_row.iloc[0].dropna().to_dict())

            elif result and "error" in result:
                st.error(f"SHAP error: {result['error']}")
            else:
                st.warning("Could not retrieve SHAP explanation.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 – Analytics
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("## 📊 Analytics & Coverage")

    if df.empty:
        st.info("No data yet.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🌍 Top Countries")
            if "country" in df.columns:
                country_df = (
                    df["country"]
                    .replace("", "Unknown")
                    .fillna("Unknown")
                    .value_counts()
                    .head(15)
                    .reset_index()
                )
                country_df.columns = ["Country", "Count"]
                st.bar_chart(country_df.set_index("Country"), height=350)
            else:
                st.info("GeoIP data not yet enriched.")

        with col2:
            st.markdown("### 🔗 Top Sources")
            if "sources" in df.columns:
                source_series = (
                    df["sources"]
                    .str.split(", ")
                    .explode()
                    .str.strip()
                    .replace("", pd.NA)
                    .dropna()
                    .value_counts()
                    .reset_index()
                )
                source_series.columns = ["Source", "Count"]
                st.bar_chart(source_series.set_index("Source"), height=350)

        st.markdown("---")
        col3, col4 = st.columns(2)

        with col3:
            st.markdown("### 🌐 ISP Distribution")
            if "isp" in df.columns:
                isp_df = (
                    df["isp"]
                    .replace("", "Unknown")
                    .fillna("Unknown")
                    .value_counts()
                    .head(10)
                    .reset_index()
                )
                isp_df.columns = ["ISP", "Count"]
                st.dataframe(isp_df, use_container_width=True)
            else:
                st.info("ISP data not yet available (requires AbuseIPDB enrichment).")

        with col4:
            st.markdown("### 🕒 Freshness Over Time")
            if "last_seen" in df.columns and df["last_seen"].notna().any():
                time_df = (
                    df.dropna(subset=["last_seen"])
                    .assign(hour=df["last_seen"].dt.floor("h"))
                    .groupby("hour")
                    .size()
                    .reset_index(name="count")
                )
                st.line_chart(time_df.set_index("hour")["count"], height=250)
            else:
                st.info("No timestamp data yet.")

        st.markdown("---")
        st.markdown("### 📈 Enrichment & ML Coverage")

        enriched_count   = int(df.get("enriched", pd.Series()).eq(True).sum()) if "enriched" in df.columns else 0
        ml_scored_count  = int(df.get("ml_scored", pd.Series()).eq(True).sum()) if "ml_scored" in df.columns else 0
        total            = len(df)

        cov1, cov2, cov3 = st.columns(3)
        cov1.metric("Total IOCs",       total)
        cov2.metric("Enriched",         enriched_count,
                    delta=f"{enriched_count/total*100:.1f}%" if total else "0%")
        cov3.metric("ML Scored",        ml_scored_count,
                    delta=f"{ml_scored_count/total*100:.1f}%" if total else "0%")

        if "confidence_score" in df.columns:
            avg_conf = df["confidence_score"].dropna().mean()
            st.metric("Avg AbuseIPDB Confidence", f"{avg_conf:.1f}%" if avg_conf else "N/A")

        if "ml_score" in df.columns and df["ml_score"].notna().any():
            st.markdown("### Score Statistics")
            st.dataframe(
                df["ml_score"].dropna().describe().round(4).to_frame("ML Score"),
                use_container_width=True,
            )


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("🛡️ SentinelTI | Explainable Threat Intelligence Dashboard | Soham Shah")

# Auto refresh
if auto_refresh:
    time.sleep(120)
    st.rerun()
