# 🛡️ SentinelTI – ML Risk Scoring Engine

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)]()

A **security threat intelligence tool that uses AI to rate how "risky" an IP address is**. Think of it like a threat score for suspicious internet addresses.

> Stacking Ensemble: Random Forest + XGBoost → Linear Meta-Learner  
> SHAP: Global feature importance + Local per-IP explanation

---

## 📋 Table of Contents
- [What Does It Do?](#-what-does-it-do)
- [The Main Pieces](#-the-main-pieces)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Practical Example](#-practical-example)
- [API Reference](#-api-reference)

---

## What Does It Do?

SentinelTI takes information about an IP address (abuse reports, location, virus detections, etc.) and predicts whether it's:

-  **HIGH RISK** (score ≥ 0.7)
-  **MEDIUM RISK** (score ≥ 0.3)
-  **LOW RISK** (score < 0.3)

Perfect for security teams, threat intelligence platforms, and incident response workflows.

---

##  The Main Pieces

### 1️⃣ Feature List (Input Data)

The model analyzes 10 key threat signals:

```
abuse_reports    → How many times reported as abusive?
recency_hrs      → How long since last seen doing something bad?
confidence_pct   → How confident are we it's malicious?
vt_detections    → How many antivirus vendors flagged it?
vt_total         → Total antivirus engines checked
multi_source     → Data from multiple threat sources?
attack_type_count→ How many malware categories detected?
geo_risk         → From a high-risk country? (China, Russia, etc.)
freshness        → How recent is the threat intelligence?
source_score     → Overall threat score from aggregated sources
```

---

### 2️⃣ Data Preprocessing (`doc_to_features`)

Raw threat data is messy. This function cleans it up:

- Converts text, dates, and objects into 10 clean numbers
- Normalizes values to 0-1 range where needed
- Handles missing data with sensible defaults
- Calculates derived metrics (e.g., time since last abuse)

**Example Transformations:**
```python
Input:  "abuse_reports": 50           →  Output: 50.0
Input:  "country_code": "RU"          →  Output: 1.0 (risky country)
Input:  "country_code": "US"          →  Output: 0.0 (not risky)
Input:  "last_abuse_time": "2 hrs ago"→ Output: recency_hrs=2.0
```

---

### 3️⃣ AI Ensemble Model

**Architecture: Stacking (3-layer voting system)**

```
Layer 1: Base Learners
├── Random Forest (150 trees, depth=8)
└── XGBoost (150 trees, depth=6)
        ↓
Layer 2: Meta-Learner
└── Logistic Regression (combines votes)
        ↓
Final Score: 0.0 - 1.0 (risk probability)
```

**How it works:**
1. Random Forest independently predicts risk
2. XGBoost independently predicts risk
3. Logistic Regression combines both predictions into a final score
4. **Result:** More accurate than any single model

**Training Data:**
- 2,000 labeled examples
- 1,000 "malicious" IPs (high abuse, detections, geo-risk)
- 1,000 "safe" IPs (low risk indicators)

---

### 4️⃣ Risk Scoring (`score_document`)

Takes one IP record → Returns structured risk assessment:

```json
{
  "risk_score": 0.85,        # 0-1 (0=safe, 1=risky)
  "risk_label": "HIGH",      # HIGH | MEDIUM | LOW
  "rf_prob": 0.82,           # Random Forest vote
  "xgb_prob": 0.88,          # XGBoost vote
  "features": {              # Feature values used
    "abuse_reports": 150,
    "vt_detections": 35,
    "geo_risk": 1.0,
    ...
  }
}
```

---

### Batch Processing (`score_all`)

Process entire databases efficiently:

```python
score_all(mongodb_collection, progress_callback=my_callback)
```

- Scores all enriched IPs in database
- Stores results back to MongoDB
- Tracks progress in real-time
- Handles errors gracefully

---

##  SHAP Explainability

Most ML models are "black boxes." **SHAP makes them transparent.**

### Global SHAP: Overall Feature Importance

```
Feature              Importance    % of Total
─────────────────────────────────────────────
vt_detections        0.0125        12.5%  ← Most important
abuse_reports        0.0102        10.2%
geo_risk             0.0081         8.1%
confidence_pct       0.0075         7.5%
recency_hrs          0.0062         6.2%
...
```

**Use case:** Security teams understand which signals drive risk decisions globally.

---

### Local SHAP: Per-IP Explanations

For a single flagged IP, see exactly which features pushed it toward risk:

```
Feature          Value   SHAP Impact   Direction
────────────────────────────────────────────────
vt_detections    35      +0.42         ↑ increases_risk
abuse_reports    200     +0.25         ↑ increases_risk
confidence_pct   92      +0.18         ↑ increases_risk
geo_risk         1.0     +0.15         ↑ increases_risk
─────────────────────────────────────────────────
Base Value       0.15
Final Score      0.82    (0.15 + contributions)
```

**Use case:** Analysts ask *"Why was this IP flagged?"* and get a clear answer.

---

##  Installation

### Requirements
```
Python 3.8+
scikit-learn >= 1.0
xgboost >= 1.5
shap >= 0.40
numpy >= 1.20
pymongo >= 3.12 (for database operations)
python-dateutil >= 2.8
```

### Setup

```bash
# Clone repository
git clone https://github.com/yourorg/sentinelti.git
cd sentinelti

# Install dependencies
pip install -r requirements.txt

# Or install individually
pip install scikit-learn xgboost shap numpy pymongo python-dateutil
```

---

##  Quick Start

### 1. Score a Single IP

```python
from ml_model import score_document

doc = {
    "indicator": "192.168.1.100",
    "abuse_reports": 150,
    "confidence_score": 85,
    "vt_detections": 25,
    "vt_total": 70,
    "country_code": "RU",
    "last_abuse_time": "2024-01-15T14:30:00Z",
    "sources": ["abuseipdb", "virustotal"],
    "categories": ["malware", "botnet", "scanner"]
}

result = score_document(doc)
print(result)
# Output:
# {
#   "risk_score": 0.82,
#   "risk_label": "HIGH",
#   "rf_prob": 0.79,
#   "xgb_prob": 0.85,
#   "features": {...}
# }
```

---

### 2. Score All IPs in Database

```python
from pymongo import MongoClient
from ml_model import score_all

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["threat_intel"]
collection = db["indicators"]

# Score all enriched documents
def progress(count, total):
    print(f"Progress: {count}/{total}")

scored_count = score_all(collection, progress_cb=progress)
print(f"Scored {scored_count} indicators")
```

---

### 3. Explain Global Feature Importance

```python
from ml_model import shap_global

importance = shap_global(n_background=200)
print(importance)
# Output:
# {
#   "global_shap": [
#     {"feature": "vt_detections", "importance": 0.0125, "pct": 12.5},
#     {"feature": "abuse_reports", "importance": 0.0102, "pct": 10.2},
#     ...
#   ]
# }
```

---

### 4. Explain Single IP Decision

```python
from ml_model import shap_local, score_document

doc = {
    "indicator": "203.0.113.42",
    "abuse_reports": 200,
    "confidence_score": 92,
    "vt_detections": 35,
    "country_code": "RU",
    "last_abuse_time": "2024-01-15T14:30:00Z",
    ...
}

explanation = shap_local(doc)
print(explanation)
# Output:
# {
#   "indicator": "203.0.113.42",
#   "risk_score": 0.82,
#   "base_value": 0.15,
#   "local_shap": [
#     {
#       "feature": "vt_detections",
#       "value": 35.0,
#       "shap_value": 0.42,
#       "direction": "increases_risk"
#     },
#     ...
#   ]
# }
```

---

## Architecture

### Data Flow

```
Raw Threat Intel Data
        ↓
    [doc_to_features]
        ↓
    10 Features (normalized)
        ↓
    ┌─────────────────────────┐
    │   Stacking Ensemble     │
    ├─────────────────────────┤
    │  Random Forest (vote)   │
    │  XGBoost (vote)         │
    │  → Logistic Regression  │
    └─────────────────────────┘
        ↓
    Risk Score (0.0 - 1.0)
        ↓
    [HIGH | MEDIUM | LOW]
        ↓
    Store in MongoDB
        ↓
    [SHAP Explain] ← Why did it get flagged?
```

---

##  Practical Example

### Input: Messy Threat Intel Data

```json
{
  "indicator": "192.168.1.100",
  "abuse_reports": 150,
  "confidence_score": 85,
  "vt_detections": 25,
  "vt_total": 70,
  "country_code": "RU",
  "last_abuse_time": "2024-01-15T14:30:00Z",
  "sources": ["abuseipdb", "virustotal", "tor-project"],
  "categories": ["botnet", "scanner", "malware"],
  "score": 8.5
}
```

### Processing

```python
result = score_document(doc)
explanation = shap_local(doc)
```

### Output: Risk Assessment

```json
{
  "risk_score": 0.82,
  "risk_label": "HIGH",
  "rf_prob": 0.79,
  "xgb_prob": 0.85,
  "explanation": {
    "top_reasons": [
      "High vt_detections (25/70 = 35.7%)",
      "High abuse_reports (150 reports)",
      "High-risk country (Russia)",
      "Multiple threat categories detected"
    ]
  }
}
```

### Action

```
✅ BLOCK: IP is HIGH RISK
📧 ALERT: Security team notification
📊 LOG: Store decision + explanation for audit
```

---

##  API Reference

### `doc_to_features(doc: dict) → np.ndarray`

Converts raw IP threat data to ML-ready feature vector.

**Input:** MongoDB document with threat intel  
**Output:** 10-element numpy array (float32)

---

### `score_document(doc: dict) → dict`

Scores a single IP document.

**Input:**
```python
{
  "indicator": "1.2.3.4",
  "abuse_reports": int,
  "confidence_score": float (0-100),
  "vt_detections": int,
  "vt_total": int,
  "country_code": str (2-char),
  "last_abuse_time": datetime or str,
  "sources": list[str],
  "categories": list[str],
  "score": float
}
```

**Output:**
```python
{
  "risk_score": float (0-1),
  "risk_label": str ("HIGH" | "MEDIUM" | "LOW"),
  "rf_prob": float,
  "xgb_prob": float,
  "features": dict
}
```

---

### `score_all(collection, progress_cb=None) → int`

Batch score all enriched documents in MongoDB.

**Parameters:**
- `collection`: MongoDB collection object
- `progress_cb`: Optional callback `fn(count, total)`

**Returns:** Number of scored documents

---

### `shap_global(n_background: int = 200) → dict`

Global feature importance across all training data.

**Returns:**
```python
{
  "global_shap": [
    {
      "feature": str,
      "importance": float,
      "pct": float
    },
    ...
  ]
}
```

---

### `shap_local(doc: dict) → dict`

Per-IP SHAP explanations.

**Returns:**
```python
{
  "indicator": str,
  "risk_score": float,
  "base_value": float,
  "local_shap": [
    {
      "feature": str,
      "value": float,
      "shap_value": float,
      "direction": str ("increases_risk" | "decreases_risk")
    },
    ...
  ]
}
```

---

## Performance

- **Training:** 2-3 seconds (on 2K samples)
- **Single Prediction:** ~5ms
- **Batch (1000 IPs):** ~5 seconds
- **Model Size:** ~15MB (pickled)

---

##  High-Risk Countries

Currently flagged as `geo_risk=1.0`:

```
CN (China)        RU (Russia)       KP (North Korea)   IR (Iran)
NG (Nigeria)      RO (Romania)      BR (Brazil)        UA (Ukraine)
IN (India)        VN (Vietnam)
```

Customize in `HIGH_RISK_COUNTRIES` set.

---

##  Contributing

Contributions welcome! Areas for improvement:

- [ ] Add more threat sources (GreyNoise, Shodan, etc.)
- [ ] Tune hyperparameters (RandomizedSearchCV)
- [ ] Add drift detection (monitor model performance over time)
- [ ] Implement online learning (update with new threats)
- [ ] Reduce inference latency (ONNX export)

---


## Summary

Converts messy threat data into clean features  
Uses 3-layer AI voting system (RF + XGBoost + LR)  
Produces risk scores (0-1) + categorical labels  
Explains decisions with SHAP (why each IP got flagged)  
Integrates with MongoDB for batch processing  
Perfect for security operations + threat intelligence platforms

---

**Made with ❤️ for threat intelligence teams**
