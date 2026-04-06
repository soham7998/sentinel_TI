"""SentinelTI – SOC Dashboard | No sidebar, fully inline, mobile responsive"""
import os, time, requests, re
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timezone, timedelta

BACKEND = os.getenv("BACKEND_URL", "http://backend:8000")

st.set_page_config(page_title="SentinelTI || SOC", page_icon="🛡️",
                   layout="wide", initial_sidebar_state="collapsed")

st.markdown("""<style>
/* ── Reset & Base ── */
html,body,[class*="css"]{font-family:'JetBrains Mono','Fira Code','Courier New',monospace!important;background:#0a0e17!important;color:#c9d1d9!important;}
.stApp{background:#0a0e17!important;}
#MainMenu,footer,header,[data-testid="stSidebar"],[data-testid="collapsedControl"]{display:none!important;visibility:hidden!important;}
.block-container{padding:0 0.8rem 4rem 0.8rem!important;max-width:100%!important;}

/* ── Command bar ── */
.cmd-bar{background:linear-gradient(90deg,#0d1117,#161b22);border-bottom:1px solid #21e06a22;padding:10px 16px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin:-1rem -0.8rem 0.8rem -0.8rem;}
.cmd-logo{font-size:1rem;font-weight:800;letter-spacing:2px;color:#21e06a;}
.cmd-sub{font-size:0.6rem;color:#58a6ff;letter-spacing:1px;}
.cmd-time{font-size:0.75rem;color:#21e06a;font-weight:700;font-family:monospace;}

/* ── Control bar ── */
.ctrl-panel{background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:10px 14px;margin-bottom:10px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;}

/* ── KPI ── */
.kpi-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin-bottom:10px;}
@media(max-width:768px){.kpi-grid{grid-template-columns:repeat(3,1fr);}}
@media(max-width:480px){.kpi-grid{grid-template-columns:repeat(2,1fr);}}
.kpi-card{background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:10px 12px;position:relative;overflow:hidden;}
.kpi-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;}
.kpi-card.high::before{background:#f85149;}.kpi-card.medium::before{background:#f0883e;}
.kpi-card.low::before{background:#3fb950;}.kpi-card.total::before{background:#58a6ff;}
.kpi-card.enrich::before{background:#bc8cff;}.kpi-card.ml::before{background:#21e06a;}
.kpi-val{font-size:1.8rem;font-weight:800;line-height:1;margin-bottom:2px;}
.kpi-card.high .kpi-val{color:#f85149;}.kpi-card.medium .kpi-val{color:#f0883e;}
.kpi-card.low .kpi-val{color:#3fb950;}.kpi-card.total .kpi-val{color:#58a6ff;}
.kpi-card.enrich .kpi-val{color:#bc8cff;}.kpi-card.ml .kpi-val{color:#21e06a;}
.kpi-lbl{font-size:0.58rem;color:#8b949e;text-transform:uppercase;letter-spacing:1px;}
.kpi-sub{font-size:0.56rem;color:#484f58;margin-top:1px;}

/* ── Misc ── */
.sec-hdr{font-size:0.62rem;color:#8b949e;text-transform:uppercase;letter-spacing:2px;border-bottom:1px solid #21262d;padding-bottom:4px;margin:12px 0 8px 0;}
.badge-HIGH{background:#f8514922;color:#f85149;border:1px solid #f8514966;padding:2px 8px;border-radius:3px;font-size:0.7rem;font-weight:700;}
.badge-MEDIUM{background:#f0883e22;color:#f0883e;border:1px solid #f0883e66;padding:2px 8px;border-radius:3px;font-size:0.7rem;font-weight:700;}
.badge-LOW{background:#3fb95022;color:#3fb950;border:1px solid #3fb95066;padding:2px 8px;border-radius:3px;font-size:0.7rem;font-weight:700;}
.status-pill{display:inline-block;padding:3px 10px;border-radius:20px;font-size:0.65rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;}
.status-idle{background:#3fb95022;color:#3fb950;border:1px solid #3fb95044;}
.status-running{background:#f0883e22;color:#f0883e;border:1px solid #f0883e44;}
.status-ml{background:#58a6ff22;color:#58a6ff;border:1px solid #58a6ff44;}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"]{background:#0d1117;border-bottom:1px solid #21262d;gap:0;overflow-x:auto;}
.stTabs [data-baseweb="tab"]{background:transparent;color:#8b949e;font-size:0.68rem;font-weight:600;letter-spacing:1px;text-transform:uppercase;padding:10px 14px;border-radius:0;border-bottom:2px solid transparent;white-space:nowrap;}
.stTabs [aria-selected="true"]{color:#21e06a!important;border-bottom:2px solid #21e06a!important;background:transparent!important;}

/* ── Buttons ── */
.stButton>button{background:#161b22!important;border:1px solid #21262d!important;color:#c9d1d9!important;font-size:0.72rem!important;border-radius:4px!important;}
.stButton>button:hover{border-color:#21e06a!important;color:#21e06a!important;}

/* ── Metrics ── */
[data-testid="metric-container"]{background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:8px 12px;}
[data-testid="metric-container"] label{color:#8b949e!important;font-size:0.6rem!important;text-transform:uppercase;letter-spacing:1px;}
[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#c9d1d9!important;font-size:1.4rem!important;font-weight:800!important;}

/* ── Footer ── */
.soc-footer{position:fixed;bottom:0;left:0;right:0;z-index:9999;background:linear-gradient(90deg,#0d1117,#0f1318,#0d1117);border-top:1px solid #21e06a22;padding:0 16px;height:44px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;}
.soc-footer a{display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border-radius:4px;border:1px solid #21262d;color:#8b949e;text-decoration:none;font-size:0.62rem;margin:0 2px;transition:all .2s;}
.soc-footer a:hover.li{color:#0a66c2!important;border-color:#0a66c244!important;}
.soc-footer a:hover.gh{color:#c9d1d9!important;border-color:#484f58!important;}
.soc-footer a:hover.em{color:#21e06a!important;border-color:#21e06a44!important;}
@media(max-width:600px){.soc-footer .brand{display:none;}}
</style>""", unsafe_allow_html=True)

st.markdown("""
<head>

<title>SentinelTI | Explainable Threat Intelligence</title>

<meta name="title" content="An Explainable Machine Learning Framework for IP Threat Intelligence and Maliciousness Risk Scoring">
<meta name="description" content="— Soham Shah | SentinelTI SOC Dashboard for real-time threat intelligence and ML-based risk scoring">

<!-- Open Graph (LinkedIn / WhatsApp / Facebook) -->
<meta property="og:type" content="website">
<meta property="og:url" content="https://sentinelit.up.railway.app/">
<meta property="og:title" content="An Explainable Machine Learning Framework for IP Threat Intelligence and Maliciousness Risk Scoring">
<meta property="og:description" content="— Soham Shah">

<!-- Twitter -->
<meta property="twitter:card" content="summary_large_image">
<meta property="twitter:title" content="An Explainable Machine Learning Framework for IP Threat Intelligence and Maliciousness Risk Scoring">
<meta property="twitter:description" content="— Soham Shah">

</head>
""", unsafe_allow_html=True)

# ── Helpers ──
def api(path, method="GET", silent=False, **kw):
    try:
        fn = requests.post if method=="POST" else requests.get
        r  = fn(f"{BACKEND}{path}", timeout=8, **kw)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        if not silent: st.error(f"⚠ Backend: {e}")
        return None

def load_df():
    data = api("/indicators?limit=200", silent=True)
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data)
    if df.empty: return df
    if "sources" in df.columns:
        df["sources"] = df["sources"].apply(lambda x:", ".join(x) if isinstance(x,list) else str(x or ""))
    for col in ["confidence_score","abuse_reports","ml_score","rf_prob","xgb_prob"]:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["country","city","isp"]:
        if col in df.columns: df[col] = df[col].replace([None,"None","nan",""],"—").fillna("—")
    if "ml_risk" not in df.columns: df["ml_risk"] = df.get("risk","LOW")
    df["ml_risk"] = df["ml_risk"].fillna("LOW")
    if "ml_score" not in df.columns: df["ml_score"] = None
    if "enriched" not in df.columns: df["enriched"] = False
    df["STATUS"] = df["enriched"].apply(lambda x:"ENRICHED" if x is True else "PENDING")
    for col in ("first_seen","last_seen"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M").fillna("—")
    return df

def crow(row):
    r = row.get("ml_risk","")
    if r=="HIGH":   return ["background-color:#f8514918;color:#f0b4b0"]*len(row)
    if r=="MEDIUM": return ["background-color:#f0883e18;color:#f0c090"]*len(row)
    return ["color:#8b949e"]*len(row)

def now_utc():
    utc = datetime.now(timezone.utc)
    ist = utc + timedelta(hours=5, minutes=30)
    return f"{utc.strftime('%H:%M:%S')} UTC · {ist.strftime('%H:%M:%S')} IST"

# ── Load ──
status        = api("/status", silent=True) or {}
fetch_running = status.get("fetch_in_progress", False)
ml_running    = status.get("ml_in_progress", False)
df            = load_df()
total_iocs    = status.get("total",0)
high_c        = status.get("high",0)
med_c         = status.get("medium",0)
low_c         = status.get("low",0)
enr_n         = status.get("enriched",0)
ml_n          = status.get("ml_scored",0)

# ── STATUS PILL ──
if fetch_running: spill='<span class="status-pill status-running">● ENRICHING</span>'
elif ml_running:  spill='<span class="status-pill status-ml">● ML SCORING</span>'
else:             spill='<span class="status-pill status-idle">● OPERATIONAL</span>'

# ── COMMAND BAR ──
clock_slot = st.empty()
clock_slot.markdown(f"""<div class="cmd-bar">
  <div><div class="cmd-logo">🛡 SENTINELTI</div>
       <div class="cmd-sub">EXPLAINABLE THREAT INTELLIGENCE PLATFORM</div></div>
  <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
    {spill}
    <div class="cmd-time">🕐 {now_utc()}</div>
  </div>
</div>""", unsafe_allow_html=True)

# ── KPI CARDS ──
st.markdown(f"""<div class="kpi-grid">
  <div class="kpi-card total"><div class="kpi-val">{total_iocs}</div><div class="kpi-lbl">Total IOCs</div><div class="kpi-sub">Active</div></div>
  <div class="kpi-card high"><div class="kpi-val">{high_c}</div><div class="kpi-lbl">HIGH</div><div class="kpi-sub">Action needed</div></div>
  <div class="kpi-card medium"><div class="kpi-val">{med_c}</div><div class="kpi-lbl">MEDIUM</div><div class="kpi-sub">Review</div></div>
  <div class="kpi-card low"><div class="kpi-val">{low_c}</div><div class="kpi-lbl">LOW</div><div class="kpi-sub">Monitor</div></div>
  <div class="kpi-card enrich"><div class="kpi-val">{enr_n}</div><div class="kpi-lbl">Enriched</div><div class="kpi-sub">{f'{enr_n/max(total_iocs,1)*100:.0f}%' if total_iocs else '—'}</div></div>
  <div class="kpi-card ml"><div class="kpi-val">{ml_n}</div><div class="kpi-lbl">ML Scored</div><div class="kpi-sub">RF+XGBoost</div></div>
</div>""", unsafe_allow_html=True)

# Progress bars
if fetch_running:
    st.progress(enr_n/max(total_iocs,1), text=f"Enriching {enr_n}/{total_iocs} — AbuseIPDB · VirusTotal · GeoIP")
if ml_running:
    p = api("/ml/score/progress", silent=True) or {}
    st.progress(p.get("scored",0)/max(p.get("total",1),1), text=f"ML Scoring {p.get('scored',0)}/{p.get('total',0)}")

# ── CONTROL BAR (replaces sidebar — always visible) ──
st.markdown('<div class="sec-hdr">COMMAND PANEL</div>', unsafe_allow_html=True)
cb1,cb2,cb3,cb4,cb5,cb6,cb7 = st.columns([1.2,1.6,1.6,1.6,1.8,1.2,1])
with cb1:
    lim = st.select_slider("Limit", options=[25,50,100,200], value=50, label_visibility="collapsed")
with cb2:
    if st.button("⬆ FETCH FEEDS", disabled=fetch_running, use_container_width=True):
        api(f"/fetch?limit={lim}", method="POST")
        st.toast(f"Fetching {lim} IOCs…", icon="📡"); time.sleep(1); st.rerun()
with cb3:
    if st.button(" ML SCORING", disabled=(fetch_running or ml_running), use_container_width=True):
        api("/ml/score", method="POST")
        st.toast("ML scoring started",); time.sleep(1); st.rerun()
with cb4:
    if st.button("🗑 CLEAR DB", disabled=fetch_running, use_container_width=True):
        r = api("/clear", method="POST")
        if r: st.toast(f"Cleared {r.get('deleted',0)} IOCs", icon="🗑️")
        time.sleep(0.3); st.rerun()
with cb5:
    feeds = f"{'⏳' if fetch_running else '✅'} {enr_n}/{total_iocs} enriched · {'⏳' if ml_running else '✅'} {ml_n} scored"
    st.markdown(f'<div style="font-size:0.62rem;color:#8b949e;padding:8px 0;line-height:1.4">{feeds}</div>', unsafe_allow_html=True)
with cb6:
    auto_refresh = st.checkbox("🔄 Auto 30s", value=False)
with cb7:
    if st.button("↺ REFRESH", use_container_width=True):
        st.rerun()

st.markdown("<hr style='border:none;border-top:1px solid #21262d;margin:4px 0 8px 0'>", unsafe_allow_html=True)

# ── TABS ──
tab1,tab2,tab3,tab4,tab5,tab6 = st.tabs([
    "OFFENSE QUEUE","ML RISK ENGINE","SHAP · GLOBAL","SHAP · LOCAL","ANALYTICS","THREAT INTEL · LIVE"
])

# ── TAB 1 ──
with tab1:
    st.markdown('<div class="sec-hdr">ACTIVE OFFENSE QUEUE — INDICATORS OF COMPROMISE</div>', unsafe_allow_html=True)
    if df.empty and not fetch_running:
        st.markdown('<div style="text-align:center;padding:60px;color:#484f58;border:1px dashed #21262d;border-radius:6px;margin-top:20px"><div style="font-size:2.5rem">📡</div><div style="font-size:0.9rem;margin-top:12px;letter-spacing:1px">NO ACTIVE THREATS</div><div style="font-size:0.7rem;margin-top:6px">Click FETCH FEEDS above to pull live threat intelligence</div></div>', unsafe_allow_html=True)
    elif df.empty and fetch_running:
        st.info(f"⏳ Fetching IOCs… {enr_n}/{total_iocs} enriched. Table populates automatically.")
        time.sleep(3); st.rerun()
    else:
        if fetch_running:
            st.info(f"⏳ Enrichment running — {enr_n}/{total_iocs} done. Updates every 5s.")
        fc1,fc2,fc3,fc4 = st.columns([2,1.5,1.5,2])
        with fc1: search  = st.text_input("🔍", placeholder="Search IP or source…", label_visibility="collapsed")
        with fc2: risk_f  = st.multiselect("RISK", ["HIGH","MEDIUM","LOW"], default=["HIGH","MEDIUM","LOW"], label_visibility="collapsed")
        with fc3: enr_f   = st.selectbox("STATUS", ["All","ENRICHED","PENDING"], label_visibility="collapsed")
        with fc4: sort_by = st.selectbox("SORT", ["ml_score ↓","abuse_reports ↓","confidence_score ↓","last_seen ↓"], label_visibility="collapsed")
        fdf = df.copy()
        if risk_f and "ml_risk" in fdf.columns: fdf = fdf[fdf["ml_risk"].isin(risk_f)]
        if enr_f=="ENRICHED":  fdf = fdf[fdf["enriched"]==True]
        elif enr_f=="PENDING": fdf = fdf[fdf["enriched"]!=True]
        if search and "indicator" in fdf.columns:
            mask = fdf["indicator"].str.contains(search, na=False)
            if "sources" in fdf.columns: mask |= fdf["sources"].str.contains(search, na=False, case=False)
            fdf = fdf[mask]
        sc = sort_by.split(" ")[0]
        if sc in fdf.columns: fdf = fdf.sort_values(sc, ascending=False, na_position="last")
        show = [c for c in ["indicator","ml_risk","ml_score","sources","confidence_score","abuse_reports","country","city","isp","STATUS","first_seen","last_seen"] if c in fdf.columns]
        ren  = {"indicator":"IP ADDRESS","ml_risk":"SEVERITY","ml_score":"RISK SCORE","sources":"FEED SOURCE","confidence_score":"CONFIDENCE %","abuse_reports":"ABUSE REPORTS","country":"COUNTRY","city":"CITY","isp":"ISP / ASN","STATUS":"STATUS","first_seen":"FIRST SEEN","last_seen":"LAST SEEN"}
        st.dataframe(fdf[show].rename(columns=ren).style.apply(crow,axis=1), width="stretch", height=480, hide_index=True)
        c1,c2,c3 = st.columns(3)
        c1.caption(f"Showing **{len(fdf)}** of **{len(df)}** indicators")
        if fetch_running: c2.caption(f"⏳ Enriching {enr_n}/{total_iocs}…")
        c3.caption(f"🕐 {now_utc()}")
        if fetch_running: time.sleep(5); st.rerun()
# with tab1:
#     st.markdown('<div class="sec-hdr">ACTIVE OFFENSE QUEUE — INDICATORS OF COMPROMISE</div>', unsafe_allow_html=True)
#     if df.empty and not fetch_running:
#         st.markdown('<div style="text-align:center;padding:60px;color:#484f58;border:1px dashed #21262d;border-radius:6px;margin-top:20px"><div style="font-size:2.5rem">📡</div><div style="font-size:0.9rem;margin-top:12px;letter-spacing:1px">NO ACTIVE THREATS</div><div style="font-size:0.7rem;margin-top:6px">Click FETCH FEEDS above to pull live threat intelligence</div></div>', unsafe_allow_html=True)
#     elif df.empty and fetch_running:
#         st.info(f"⏳ Fetching IOCs… {enr_n}/{total_iocs} enriched. Table populates automatically.")
#         time.sleep(3); st.rerun()
#     else:
#         if fetch_running:
#             st.info(f"⏳ Enrichment running — {enr_n}/{total_iocs} done. Updates every 5s.")
#         fc1,fc2,fc3,fc4 = st.columns([2,1.5,1.5,2])
#         with fc1: search  = st.text_input("🔍", placeholder="Search IP or source…", label_visibility="collapsed")
#         with fc2: risk_f  = st.multiselect("RISK", ["HIGH","MEDIUM","LOW"], default=["HIGH","MEDIUM","LOW"], label_visibility="collapsed")
#         with fc3: enr_f   = st.selectbox("STATUS", ["All","ENRICHED","PENDING"], label_visibility="collapsed")
#         with fc4: sort_by = st.selectbox("SORT", ["ml_score ↓","abuse_reports ↓","confidence_score ↓","last_seen ↓"], label_visibility="collapsed")
#         fdf = df.copy()
#         if risk_f and "ml_risk" in fdf.columns: fdf = fdf[fdf["ml_risk"].isin(risk_f)]
#         if enr_f=="ENRICHED":  fdf = fdf[fdf["enriched"]==True]
#         elif enr_f=="PENDING": fdf = fdf[fdf["enriched"]!=True]
#         if search and "indicator" in fdf.columns:
#             mask = fdf["indicator"].str.contains(search, na=False)
#             if "sources" in fdf.columns: mask |= fdf["sources"].str.contains(search, na=False, case=False)
#             fdf = fdf[mask]
#         sc = sort_by.split(" ")[0]
#         if sc in fdf.columns: fdf = fdf.sort_values(sc, ascending=False, na_position="last")
#         show = [c for c in ["indicator","ml_risk","ml_score","sources","confidence_score","abuse_reports","country","city","isp","STATUS","first_seen","last_seen"] if c in fdf.columns]
#         ren  = {"indicator":"IP ADDRESS","ml_risk":"SEVERITY","ml_score":"RISK SCORE","sources":"FEED SOURCE","confidence_score":"CONFIDENCE %","abuse_reports":"ABUSE REPORTS","country":"COUNTRY","city":"CITY","isp":"ISP / ASN","STATUS":"STATUS","first_seen":"FIRST SEEN","last_seen":"LAST SEEN"}
#         st.dataframe(fdf[show].rename(columns=ren).style.apply(crow,axis=1), width="stretch", height=480, hide_index=True)
#         c1,c2,c3 = st.columns(3)
#         c1.caption(f"Showing **{len(fdf)}** of **{len(df)}** indicators")
#         if fetch_running: c2.caption(f"⏳ Enriching {enr_n}/{total_iocs}…")
#         c3.caption(f"🕐 {now_utc()}")
#         if fetch_running: time.sleep(5); st.rerun()

# ── TAB 2 ──
with tab2:
    st.markdown('<div class="sec-hdr">ML RISK ENGINE — RF+XGBOOST STACKING ENSEMBLE</div>', unsafe_allow_html=True)
    if df.empty or "ml_score" not in df.columns or df["ml_score"].isna().all():
        st.info("Click ML SCORING above after fetching IOCs.")
    else:
        sdf = df[df["ml_score"].notna()].copy()
        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("SCORED",len(sdf)); m2.metric("HIGH",int((sdf["ml_risk"]=="HIGH").sum()))
        m3.metric("MEDIUM",int((sdf["ml_risk"]=="MEDIUM").sum())); m4.metric("LOW",int((sdf["ml_risk"]=="LOW").sum()))
        m5.metric("AVG SCORE",f"{pd.to_numeric(sdf['ml_score'],errors='coerce').mean():.3f}")
        ca,cb = st.columns(2)
        with ca:
            scores = pd.to_numeric(sdf["ml_score"],errors="coerce").dropna()
            cnts,edges = np.histogram(scores,bins=20,range=(0,1))
            st.bar_chart(pd.DataFrame({"Score":[f"{edges[i]:.2f}" for i in range(len(edges)-1)],"Count":cnts}).set_index("Score"),height=200,color="#58a6ff")
        with cb:
            rc = sdf["ml_risk"].value_counts()
            st.bar_chart(pd.DataFrame({"Level":rc.index,"Count":rc.values}).set_index("Level"),height=200)
        st.markdown('<div class="sec-hdr">HIGH SEVERITY OFFENSES</div>', unsafe_allow_html=True)
        hdf = sdf[sdf["ml_risk"]=="HIGH"].sort_values("ml_score",ascending=False).head(25)
        sh  = [c for c in ["indicator","ml_score","rf_prob","xgb_prob","sources","confidence_score","abuse_reports","country","isp"] if c in hdf.columns]
        rn  = {"indicator":"IP","ml_score":"SCORE","rf_prob":"RF","xgb_prob":"XGB","sources":"FEEDS","confidence_score":"CONF%","abuse_reports":"REPORTS","country":"COUNTRY","isp":"ISP"}
        st.dataframe(hdf[sh].rename(columns=rn).style.apply(crow,axis=1), width="stretch", height=280, hide_index=True)
        st.markdown('<div class="sec-hdr">MODEL ARCHITECTURE</div>', unsafe_allow_html=True)
        ma1,ma2,ma3,ma4 = st.columns(4)
        for col,label,name,desc,color in [
            (ma1,"BASE LEARNER 1","Random Forest","150 estimators · max_depth=8","#58a6ff"),
            (ma2,"BASE LEARNER 2","XGBoost","150 rounds · lr=0.05 · depth=6","#f0883e"),
            (ma3,"META LEARNER","Logistic Reg","Linear · β₁·RF + β₂·XGB","#21e06a"),
            (ma4,"VALIDATION","5-Fold CV","Stratified · stack_method=proba","#bc8cff"),
        ]:
            col.markdown(f'<div style="background:#0d1117;border:1px solid #21262d;border-top:3px solid {color};border-radius:6px;padding:10px 12px"><div style="font-size:0.58rem;color:#8b949e;letter-spacing:1px;margin-bottom:4px">{label}</div><div style="font-size:0.95rem;font-weight:700;color:{color};margin-bottom:4px">{name}</div><div style="font-size:0.62rem;color:#3fb950">{desc}</div></div>', unsafe_allow_html=True)

# ── TAB 3 ──
with tab3:
    st.markdown('<div class="sec-hdr">SHAP GLOBAL — FEATURE IMPORTANCE ACROSS ALL IOCs</div>', unsafe_allow_html=True)
    st.caption("Mean |SHAP value| — which features drive malicious IP predictions globally")
    if st.button("⚡ COMPUTE GLOBAL SHAP", type="primary"):
        with st.spinner("Computing SHAP…"):
            result = api("/ml/shap/global")
        if result and "global_shap" in result:
            shap_df = pd.DataFrame(result["global_shap"]).sort_values("importance",ascending=False)
            max_imp = shap_df["importance"].max()
            for _,row in shap_df.iterrows():
                pw = int(row["importance"]/max(max_imp,0.001)*100)
                st.markdown(f'<div style="display:grid;grid-template-columns:140px 1fr 70px 55px;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid #21262d18"><div style="font-size:0.7rem;color:#c9d1d9;font-family:monospace">{row["feature"]}</div><div style="background:#21262d;border-radius:2px;height:12px"><div style="width:{pw}%;background:linear-gradient(90deg,#58a6ff66,#58a6ff);height:12px;border-radius:2px"></div></div><div style="font-size:0.68rem;color:#58a6ff;text-align:right">{row["importance"]:.5f}</div><div style="font-size:0.68rem;color:#8b949e;text-align:right">{row["pct"]:.1f}%</div></div>', unsafe_allow_html=True)
        elif result and "error" in result: st.error(f"SHAP error: {result['error']}")
    else:
        st.markdown('<div style="text-align:center;padding:40px;color:#484f58;border:1px dashed #21262d;border-radius:6px"><div style="font-size:1.5rem">🔍</div><div style="font-size:0.8rem;margin-top:8px">Click COMPUTE GLOBAL SHAP</div></div>', unsafe_allow_html=True)

# ── TAB 4 ──
with tab4:
    st.markdown('<div class="sec-hdr">SHAP LOCAL — PER-IP THREAT EXPLANATION</div>', unsafe_allow_html=True)
    if df.empty:
        st.info("No indicators loaded.")
    else:
        high_ips = df[df["ml_risk"]=="HIGH"]["indicator"].dropna().tolist()
        med_ips  = df[df["ml_risk"]=="MEDIUM"]["indicator"].dropna().tolist()
        other_ips= df[~df["ml_risk"].isin(["HIGH","MEDIUM"])]["indicator"].dropna().tolist()
        all_ips  = high_ips+med_ips+other_ips
        ic,bc = st.columns([3,1])
        with ic:
            sel = st.selectbox("IP", all_ips, format_func=lambda ip:f"{'🔴' if ip in high_ips else '🟡' if ip in med_ips else '🟢'} {ip}", label_visibility="collapsed")
        with bc:
            go = st.button("⚡ EXPLAIN", type="primary", use_container_width=True)
        if go:
            with st.spinner(f"Computing SHAP for {sel}…"):
                result = api(f"/ml/shap/local/{sel}")
            if result and "local_shap" in result:
                rs=result.get("risk_score",0); bv=result.get("base_value",0)
                rl="HIGH" if rs>=0.7 else "MEDIUM" if rs>=0.3 else "LOW"
                sc="#f85149" if rl=="HIGH" else "#f0883e" if rl=="MEDIUM" else "#3fb950"
                st.markdown(f'<div style="background:#0d1117;border:1px solid {sc}44;border-left:3px solid {sc};border-radius:6px;padding:14px 18px;margin:8px 0"><div style="display:flex;justify-content:space-between;align-items:center"><div><div style="font-size:1rem;font-weight:800;color:#c9d1d9;font-family:monospace">{sel}</div><div style="font-size:0.62rem;color:#8b949e;margin-top:4px">BASELINE: {bv:.4f} · DELTA: +{rs-bv:.4f}</div></div><div style="text-align:right"><div style="font-size:1.8rem;font-weight:900;color:{sc}">{rs:.4f}</div><span class="badge-{rl}">{rl}</span></div></div></div>', unsafe_allow_html=True)
                sldf=pd.DataFrame(result["local_shap"]); max_ab=sldf["shap_value"].abs().max()
                st.markdown('<div class="sec-hdr">FEATURE CONTRIBUTION WATERFALL</div>', unsafe_allow_html=True)
                for _,row in sldf.iterrows():
                    sv=row["shap_value"]; pw=int(abs(sv)/max(max_ab,0.001)*100)
                    bc2="#f85149" if sv>0 else "#3fb950"; arr="▲" if sv>0 else "▼"
                    st.markdown(f'<div style="display:grid;grid-template-columns:130px 55px 1fr 85px 100px;align-items:center;gap:6px;padding:4px 0;border-bottom:1px solid #21262d18"><div style="font-size:0.68rem;color:#c9d1d9;font-family:monospace">{row["feature"]}</div><div style="font-size:0.65rem;color:#8b949e;text-align:right">{row["value"]:.3f}</div><div style="background:#21262d18;border-radius:2px;height:10px"><div style="width:{pw}%;background:{bc2}88;height:10px;border-radius:2px"></div></div><div style="font-size:0.68rem;color:{bc2};text-align:right;font-weight:700">{arr} {abs(sv):.5f}</div><div style="font-size:0.58rem;color:{bc2};letter-spacing:0.5px">{"RISK ↑" if sv>0 else "RISK ↓"}</div></div>', unsafe_allow_html=True)
                ipr=df[df["indicator"]==sel]
                if not ipr.empty:
                    with st.expander("📋 FULL IOC RECORD"):
                        rec=ipr.iloc[0].dropna().to_dict(); c1,c2,c3=st.columns(3); flds=list(rec.items()); t=len(flds)//3
                        for k,v in flds[:t]: c1.markdown(f'<div style="font-size:0.68rem"><span style="color:#8b949e">{k}:</span> {v}</div>', unsafe_allow_html=True)
                        for k,v in flds[t:t*2]: c2.markdown(f'<div style="font-size:0.68rem"><span style="color:#8b949e">{k}:</span> {v}</div>', unsafe_allow_html=True)
                        for k,v in flds[t*2:]: c3.markdown(f'<div style="font-size:0.68rem"><span style="color:#8b949e">{k}:</span> {v}</div>', unsafe_allow_html=True)
            elif result and "error" in result: st.error(f"SHAP: {result['error']}")
        else:
            st.markdown('<div style="text-align:center;padding:40px;color:#484f58;border:1px dashed #21262d;border-radius:6px"><div style="font-size:1.5rem">🔎</div><div style="font-size:0.8rem;margin-top:8px">Select IP → EXPLAIN · HIGH risk IPs listed first</div></div>', unsafe_allow_html=True)

# ── TAB 5 ──
with tab5:
    st.markdown('<div class="sec-hdr">THREAT ANALYTICS & INTELLIGENCE COVERAGE</div>', unsafe_allow_html=True)
    if df.empty:
        st.info("No data yet.")
    else:
        r1,r2 = st.columns(2)
        with r1:
            st.markdown('<div class="sec-hdr">TOP COUNTRIES</div>', unsafe_allow_html=True)
            if "country" in df.columns and df["country"].ne("—").any():
                cdf=df[df["country"]!="—"]["country"].value_counts().head(12).reset_index(); cdf.columns=["Country","Count"]
                st.bar_chart(cdf.set_index("Country"),height=240,color="#f85149")
        with r2:
            st.markdown('<div class="sec-hdr">FEED BREAKDOWN</div>', unsafe_allow_html=True)
            if "sources" in df.columns:
                sdf2=df["sources"].str.split(", ").explode().str.strip().replace("",pd.NA).dropna().value_counts().reset_index(); sdf2.columns=["Source","Count"]
                st.bar_chart(sdf2.set_index("Source"),height=240,color="#58a6ff")
        r2a,r2b = st.columns(2)
        with r2a:
            st.markdown('<div class="sec-hdr">ISP ATTRIBUTION</div>', unsafe_allow_html=True)
            if "isp" in df.columns and df["isp"].ne("—").any():
                idf=df[df["isp"]!="—"]["isp"].value_counts().head(10).reset_index(); idf.columns=["ISP","Count"]
                st.dataframe(idf, width="stretch", hide_index=True, height=220)
        with r2b:
            st.markdown('<div class="sec-hdr">INGESTION TIMELINE</div>', unsafe_allow_html=True)
            if "last_seen" in df.columns:
                tdf=df[df["last_seen"]!="—"].copy(); tdf["t"]=pd.to_datetime(tdf["last_seen"],errors="coerce").dt.floor("10min")
                tdf=tdf.dropna(subset=["t"]).groupby("t").size().reset_index(name="IOCs")
                if not tdf.empty: st.line_chart(tdf.set_index("t")["IOCs"],height=220,color="#21e06a")
        st.markdown('<div class="sec-hdr">COVERAGE METRICS</div>', unsafe_allow_html=True)
        cv1,cv2,cv3,cv4,cv5 = st.columns(5)
        tot2=len(df); enrc=int(df["enriched"].eq(True).sum()) if "enriched" in df.columns else 0
        mlc=int(df.get("ml_scored",pd.Series(dtype=bool)).eq(True).sum()) if "ml_scored" in df.columns else 0
        avgc=pd.to_numeric(df.get("confidence_score"),errors="coerce").mean() if "confidence_score" in df.columns else 0
        avgs=pd.to_numeric(df.get("ml_score"),errors="coerce").mean() if "ml_score" in df.columns else 0
        cv1.metric("TOTAL IOCs",tot2); cv2.metric("ENRICHED",enrc,delta=f"{enrc/max(tot2,1)*100:.0f}%")
        cv3.metric("ML SCORED",mlc,delta=f"{mlc/max(tot2,1)*100:.0f}%")
        cv4.metric("AVG CONFIDENCE",f"{avgc:.1f}%" if avgc else "—")
        cv5.metric("AVG ML SCORE",f"{avgs:.3f}" if avgs else "—")

# ── TAB 6 ──
with tab6:
    st.markdown('<div class="sec-hdr">GLOBAL THREAT INTELLIGENCE — LAST 48 HOURS</div>', unsafe_allow_html=True)
    st.caption("Live cybersecurity news · CVEs · Ransomware · Nation-state activity")
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime
    news_sources=[
        ("https://feeds.feedburner.com/TheHackersNews","The Hacker News","#f85149"),
        ("https://www.bleepingcomputer.com/feed/","BleepingComputer","#f0883e"),
        ("https://isc.sans.edu/rssfeed_full.xml","SANS ISC","#58a6ff"),
        ("https://www.darkreading.com/rss.xml","Dark Reading","#bc8cff"),
        ("https://cybersecuritynews.com/feed/","CyberSecurity News","#21e06a"),
        ("https://securityaffairs.com/feed","Security Affairs","#8b949e"),
    ]
    all_articles=[]; cutoff=datetime.now(timezone.utc)-timedelta(hours=48)
    for feed_url,feed_name,feed_color in news_sources:
        try:
            r=requests.get(feed_url,timeout=8,headers={"User-Agent":"SentinelTI/2.0"})
            root=ET.fromstring(r.content)
            for item in root.findall(".//item")[:12]:
                title=item.findtext("title","").strip(); link=item.findtext("link","").strip()
                desc=re.sub(r"<[^>]+>","",item.findtext("description",""))[:200].strip()
                try:
                    pub_dt=parsedate_to_datetime(item.findtext("pubDate",""))
                    if pub_dt.tzinfo is None: pub_dt=pub_dt.replace(tzinfo=timezone.utc)
                except: pub_dt=datetime.now(timezone.utc)
                if pub_dt>=cutoff: all_articles.append({"source":feed_name,"color":feed_color,"title":title,"link":link,"time":pub_dt,"summary":desc})
        except Exception as e: st.caption(f"⚠ {feed_name}: {e}")
    all_articles.sort(key=lambda x:x["time"],reverse=True)
    if not all_articles:
        st.info("No recent articles. Feeds may be temporarily unavailable.")
    else:
        src_avail=list(set(a["source"] for a in all_articles))
        sel_src=st.multiselect("FILTER",src_avail,default=src_avail,label_visibility="collapsed")
        filtered=[a for a in all_articles if a["source"] in sel_src]
        st.caption(f"📰 {len(filtered)} articles · last 48h")
        for art in filtered:
            ist_t=art["time"]+timedelta(hours=5,minutes=30)
            age_sec=(datetime.now(timezone.utc)-art["time"]).total_seconds()
            age_str=f"{age_sec/3600:.0f}h ago" if age_sec>=3600 else f"{age_sec/60:.0f}m ago"
            c=art["color"]
            st.markdown(f'''<div style="background:#0d1117;border:1px solid #21262d;border-left:3px solid {c};border-radius:6px;padding:10px 14px;margin-bottom:8px"><div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px"><div style="flex:1"><a href="{art['link']}" target="_blank" style="font-size:0.82rem;font-weight:700;color:#c9d1d9;text-decoration:none;line-height:1.3;display:block;margin-bottom:4px">{art['title']}</a><div style="font-size:0.7rem;color:#8b949e;line-height:1.4">{art['summary']}…</div></div><div style="text-align:right;min-width:130px;flex-shrink:0"><div style="font-size:0.62rem;color:{c};font-weight:700;letter-spacing:1px">{art['source']}</div><div style="font-size:0.6rem;color:#484f58;margin-top:3px">{art['time'].strftime('%H:%M')} UTC · {ist_t.strftime('%H:%M')} IST</div><div style="font-size:0.6rem;color:#484f58">{age_str}</div></div></div></div>''', unsafe_allow_html=True)

# ── FOOTER ──
st.markdown("""
<div class="soc-footer">
  <div style="display:flex;align-items:center;gap:4px">
    <span style="font-size:0.58rem;color:#484f58;letter-spacing:1px;margin-right:4px">BUILT BY</span>
    <a class="li" href="https://www.linkedin.com/in/shahsoham2003/" target="_blank" rel="noopener"
       style="display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border-radius:4px;border:1px solid #21262d;color:#8b949e;text-decoration:none;font-size:0.62rem"
       onmouseover="this.style.color='#0a66c2';this.style.borderColor='#0a66c244';this.style.background='#0a66c211'"
       onmouseout="this.style.color='#8b949e';this.style.borderColor='#21262d';this.style.background='transparent'">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-4 0v7h-4v-7a6 6 0 0 1 6-6z"/><rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/></svg>
      Soham Shah
    </a>
    <a class="gh" href="https://github.com/soham7998/sentinel_TI" target="_blank" rel="noopener"
       style="display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border-radius:4px;border:1px solid #21262d;color:#8b949e;text-decoration:none;font-size:0.62rem"
       onmouseover="this.style.color='#c9d1d9';this.style.borderColor='#484f58';this.style.background='#21262d'"
       onmouseout="this.style.color='#8b949e';this.style.borderColor='#21262d';this.style.background='transparent'">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/></svg>
      sentinel_TI
    </a>
    <a class="em" href="mailto:soham27@somaiya.edu"
       style="display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border-radius:4px;border:1px solid #21262d;color:#8b949e;text-decoration:none;font-size:0.62rem"
       onmouseover="this.style.color='#21e06a';this.style.borderColor='#21e06a44';this.style.background='#21e06a11'"
       onmouseout="this.style.color='#8b949e';this.style.borderColor='#21262d';this.style.background='transparent'">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
      soham27@somaiya.edu
    </a>
  </div>
  <div class="brand" style="font-size:0.62rem;color:#484f58;display:flex;align-items:center;gap:6px">
    <span style="font-size:0.72rem;font-weight:800;color:#21e06a;letter-spacing:2px">🛡 SENTINELTI </span>
    <span style="color:#21262d">·</span>© 2026
  </div>
</div>
""", unsafe_allow_html=True)

# ── LIVE CLOCK — always ticks 30s then rerun ──
for _ in range(30):
    clock_slot.markdown(f"""<div class="cmd-bar">
  <div><div class="cmd-logo">🛡 SENTINELTI</div>
       <div class="cmd-sub">EXPLAINABLE THREAT INTELLIGENCE PLATFORM</div></div>
  <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
    {spill}
    <div class="cmd-time">🕐 {now_utc()}</div>
  </div>
</div>""", unsafe_allow_html=True)
    time.sleep(1)

st.rerun()
