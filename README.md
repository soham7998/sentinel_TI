# 🛡️ SentinelTI — Explainable Threat Intelligence Dashboard

**MSc Sem-4 Research Project || Somaiya Vidyavihar University**

> An Explainable Machine Learning Framework for IP Threat Intelligence and Maliciousness Risk Scoring

---

## 📌 Overview

SentinelTI is a real-time, SOC-ready threat intelligence dashboard that:
- Ingests IP indicators from **Abuse.ch** and **CINS Army** feeds
- Enriches them asynchronously via **VirusTotal**, **AbuseIPDB**, and **GeoIP**
- Scores maliciousness using a **Random Forest + XGBoost stacking ensemble**
- Explains every prediction using **SHAP** (global + local explainability)
- Displays everything on a **Streamlit SOC dashboard** with LOW / MEDIUM / HIGH risk tiers

---

## 🏗️ Architecture

```
External Feeds (Abuse.ch, CINS Army)
        ↓
Fast IOC Ingestion (Normalize, Deduplicate, Limit)
        ↓
Async Enrichment (VirusTotal, AbuseIPDB, GeoIP/ASN)
        ↓
MongoDB IOC Store (Timestamps, Features, Scores)
        ↓
ML Risk Scoring Engine (RF + XGBoost Stacking, Score 0–1)
        ↓
SHAP Explainability (Global Feature Importance + Local Per-IP)
        ↓
SOC Dashboard (LOW / MEDIUM / HIGH — Evidence-based Decisions)
```

---

## 🚀 Quickstart

### Prerequisites
- Docker + Docker Compose
- API keys (free tier):
  - [AbuseIPDB](https://www.abuseipdb.com/register)
  - [VirusTotal](https://www.virustotal.com/gui/join-us)


## 🖥️ Dashboard Tabs

| Tab | Description |
|---|---|
| 📡 Live Feed | Real-time IOC table with risk colouring, search, filters |
| 🧠 ML Risk Scoring | Score distribution, HIGH/MEDIUM/LOW breakdown |
| 🔍 SHAP Global | Global feature importance (mean \|SHAP\|) across all IPs |
| 🔎 SHAP Local | Per-IP waterfall explanation — what drove the score |
| 📊 Analytics | Top countries, ISPs, sources, enrichment coverage |

---

## 🧠 ML Model

**Stacking Ensemble:**
- Base learners: Random Forest (150 trees) + XGBoost (150 rounds)
- Meta-learner: Logistic Regression (interpretable coefficients)
- Risk tiers: LOW (0–0.3) | MEDIUM (0.3–0.7) | HIGH (≥0.7)

**Features used:**
| Feature | Source |
|---|---|
| `abuse_reports` | AbuseIPDB |
| `confidence_pct` | AbuseIPDB |
| `recency_hrs` | AbuseIPDB last report time |
| `vt_detections` | VirusTotal |
| `geo_risk` | GeoIP country |
| `multi_source` | Feed overlap |
| `attack_type_count` | AbuseIPDB categories |
| `freshness` | Derived from recency |
| `source_score` | Feed-level weighting |

---

## 📊 Results (from paper)

| Metric | Result | SOC Target |
|---|---|---|
| Precision | 95% | >90% |
| Recall | 93% | >85% |
| F1-Score | 94% | >90% |
| False Positive Rate | 4% | <5% |
| Data Freshness | <10s | <15s |
| Enrichment Coverage | >95% | >90% |

---

## 📁 Project Structure

```
sentinel_TI/
├── backend/
│   ├── main.py          # FastAPI endpoints
│   ├── feeds.py         # Feed ingestion + async enrichment
│   ├── ml_model.py      # RF+XGBoost stacking + SHAP
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app.py           # Streamlit SOC dashboard
│   ├── requirements.txt
│   └── Dockerfile
├── geoip/
│   └── GeoLite2-City.mmdb
├── docker-compose.yml
├── .env.sample
└── README.md
```

---

## 📄 Paper

Shah Soham, & Pawar Mousmi. — *An Explainable Machine Learning Framework for IP Threat Intelligence and Maliciousness Risk Scoring* — Somaiya Vidyavihar University, Mumbai


---

## 👤 Author

**Soham Shah** — soham27@somaiya.edu  
Department of IT & CS, Somaiya School of Basic and Applied Sciences
