import os
import streamlit as st
import requests
import pandas as pd

# -----------------------------
# CONFIG
# -----------------------------
BACKEND = os.getenv("BACKEND_URL", "http://backend:8000")

st.set_page_config(layout="wide", page_title="SentinelTI")
st.title("🛡️ SentinelTI – Threat Intelligence Dashboard")

# -----------------------------
# LEFT PANEL
# -----------------------------
col1, col2 = st.columns([1, 4])

with col1:
    if st.button("🚀 Fetch Now"):
        with st.spinner("Fetching threat feeds..."):
            try:
                r = requests.post(f"{BACKEND}/fetch", timeout=60)

                if r.status_code != 200:
                    st.error("Backend error during fetch")
                    st.code(r.text)
                else:
                    data = r.json()
                    st.success(
                        f"Inserted {data.get('inserted', 0)} indicators "
                        f"in {data.get('time_sec', 0)} sec"
                    )

            except Exception as e:
                st.error("Fetch failed")
                st.exception(e)

    limit = st.number_input("Display limit", 50, 500, 200)

# -----------------------------
# RIGHT PANEL
# -----------------------------
with col2:
    st.subheader("📌 Recent Indicators")

    try:
        r = requests.get(f"{BACKEND}/indicators?limit={limit}", timeout=30)

        if r.status_code != 200:
            st.error("Failed to load indicators")
            st.code(r.text)
            st.stop()

        data = r.json()

    except Exception as e:
        st.error("Unable to connect to backend")
        st.exception(e)
        st.stop()

    if not data:
        st.info("No data available")
        st.stop()

    df = pd.DataFrame(data)

    cols = [
        "indicator",
        "source",
        "confidence_score",
        "country",
        "state",
        "city",
        "malicious",
        "first_seen",
        "fetched_at",
    ]
    df = df[[c for c in cols if c in df.columns]]

    # -----------------------------
    # ROW COLORING
    # -----------------------------
    def color_row(row):
        if row.get("malicious", False):
            return ["background-color: #d62828; color: white"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df.style.apply(color_row, axis=1),
        use_container_width=True,
    )

    # -----------------------------
    # SUMMARY
    # -----------------------------
    st.markdown("### 🚨 Threat Summary")
    c1, c2, c3 = st.columns(3)

    c1.metric("Total", len(df))
    c2.metric("Malicious", int(df["malicious"].sum()) if "malicious" in df else 0)
    c3.metric(
        "Clean",
        int((~df["malicious"]).sum()) if "malicious" in df else 0,
    )

    # -----------------------------
    # COUNTRIES
    # -----------------------------
    if "country" in df.columns:
        st.markdown("### 🌍 Top Countries")
        st.table(
            df["country"]
            .value_counts()
            .head(10)
            .reset_index()
            .rename(columns={"index": "Country", "country": "Count"})
        )

