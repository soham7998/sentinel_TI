"""
SentinelTI – FastAPI Backend
Endpoints:
  POST /fetch              – trigger IOC ingestion + async enrichment
  GET  /status             – system status
  GET  /indicators         – list all IOCs
  POST /ml/score           – run ML scoring on all enriched IOCs
  GET  /ml/shap/global     – global SHAP feature importance
  GET  /ml/shap/local/{ip} – local SHAP explanation for one IP
"""

import os
import logging
from threading import Thread, Lock
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pymongo import MongoClient

from feeds import fetch_base_indicators, enrich_indicators
from ml_model import score_all, shap_global, shap_local, score_document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI(title="SentinelTI Backend")

MONGO_URI  = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
client     = MongoClient(MONGO_URI)
db         = client["sentinelti"]
collection = db["indicators"]

fetch_lock       = Lock()
fetch_in_progress = False
ml_in_progress   = False


# ── Background Jobs ────────────────────────────────────────────────────────────

def _background_fetch():
    global fetch_in_progress
    with fetch_lock:
        fetch_in_progress = True
    try:
        base = fetch_base_indicators(limit=200)
        now  = datetime.now(timezone.utc)

        for ioc in base:
            collection.update_one(
                {"indicator": ioc["indicator"]},
                {
                    "$setOnInsert": {"first_seen": now},
                    "$set": {
                        "sources":  ioc["sources"],
                        "score":    ioc["score"],
                        "risk":     ioc["risk"],
                        "last_seen": now,
                        "enriched": False,
                        "ml_scored": False,
                    },
                },
                upsert=True,
            )

        logger.info(f"Upserted {len(base)} base indicators")

        # kick off enrichment, then ML scoring
        Thread(target=_background_enrich_then_score, daemon=True).start()

    finally:
        fetch_in_progress = False


def _background_enrich_then_score():
    global ml_in_progress
    enrich_indicators(collection)   # blocks until done
    ml_in_progress = True
    try:
        scored = score_all(collection)
        logger.info(f"Auto ML scoring: {scored} indicators scored")
    finally:
        ml_in_progress = False


# ── API Endpoints ──────────────────────────────────────────────────────────────

@app.post("/fetch")
def fetch():
    global fetch_in_progress
    if fetch_in_progress:
        return {"status": "already_running"}
    Thread(target=_background_fetch, daemon=True).start()
    return {"status": "started"}


@app.get("/status")
def status():
    return {
        "fetch_in_progress": fetch_in_progress,
        "ml_in_progress":    ml_in_progress,
        "total":             collection.count_documents({}),
        "enriched":          collection.count_documents({"enriched": True}),
        "ml_scored":         collection.count_documents({"ml_scored": True}),
        "high":              collection.count_documents({"ml_risk": "HIGH"}),
        "medium":            collection.count_documents({"ml_risk": "MEDIUM"}),
        "low":               collection.count_documents({"ml_risk": "LOW"}),
    }


@app.get("/indicators")
def indicators(limit: int = 200):
    docs = list(
        collection.find({}, {"_id": 0})
        .sort("last_seen", -1)
        .limit(limit)
    )
    # Serialize datetime fields to ISO strings for JSON
    for doc in docs:
        for key in ("first_seen", "last_seen", "last_abuse_time"):
            val = doc.get(key)
            if hasattr(val, "isoformat"):
                doc[key] = val.isoformat()
    return docs


@app.post("/ml/score")
def ml_score():
    """Trigger ML scoring on all enriched IOCs (runs synchronously)."""
    global ml_in_progress
    if ml_in_progress:
        return {"status": "already_running"}
    ml_in_progress = True
    try:
        count = score_all(collection)
        return {"status": "done", "scored": count}
    finally:
        ml_in_progress = False


@app.get("/ml/shap/global")
def ml_shap_global():
    """Return global SHAP feature importance."""
    return shap_global(n_background=200)


@app.get("/ml/shap/local/{ip}")
def ml_shap_local(ip: str):
    """Return local SHAP explanation for a specific IP."""
    doc = collection.find_one({"indicator": ip}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail=f"IP {ip} not found")
    # Serialize datetime fields
    for key in ("first_seen", "last_seen", "last_abuse_time"):
        val = doc.get(key)
        if hasattr(val, "isoformat"):
            doc[key] = val.isoformat()
    return shap_local(doc)
