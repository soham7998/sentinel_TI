"""
SentinelTI – FastAPI Backend
"""

import os
import logging
from threading import Thread, Lock
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from pymongo import MongoClient

from feeds import fetch_base_indicators, enrich_indicators
from ml_model import score_all, shap_global, shap_local, score_document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI(title="SentinelTI Backend")

MONGO_URI  = os.getenv("MONGO_URI")
client     = MongoClient(MONGO_URI)
db         = client["sentinelti"]
collection = db["indicators"]

fetch_lock        = Lock()
fetch_in_progress = False
ml_in_progress    = False
ml_progress       = {"scored": 0, "total": 0}   # live progress tracking


def _background_fetch(limit: int = 50):
    global fetch_in_progress
    with fetch_lock:
        fetch_in_progress = True
    try:
        base = fetch_base_indicators(limit=limit)
        now  = datetime.now(timezone.utc)
        for ioc in base:
            collection.update_one(
                {"indicator": ioc["indicator"]},
                {
                    "$setOnInsert": {"first_seen": now},
                    "$set": {
                        "sources":   ioc["sources"],
                        "score":     ioc["score"],
                        "risk":      ioc["risk"],
                        "last_seen": now,
                        "enriched":  False,
                        "ml_scored": False,
                    },
                },
                upsert=True,
            )
        logger.info(f"Upserted {len(base)} base indicators")
        Thread(target=_background_enrich_then_score, daemon=True).start()
    finally:
        fetch_in_progress = False


def _background_enrich_then_score():
    global ml_in_progress, ml_progress
    enrich_indicators(collection)
    # Auto ML score after enrichment
    ml_in_progress = True
    total = collection.count_documents({"enriched": True})
    ml_progress = {"scored": 0, "total": total}
    try:
        scored = score_all(collection, progress_cb=_ml_progress_cb)
        logger.info(f"Auto ML scoring complete: {scored} indicators")
    finally:
        ml_in_progress = False


def _ml_progress_cb(n: int, total: int):
    ml_progress["scored"] = n
    ml_progress["total"]  = total


@app.on_event("startup")
def preload_model():
    """Pre-train model at startup so first /ml/score call is instant."""
    from ml_model import get_model
    Thread(target=get_model, daemon=True).start()
    logger.info("Model preload started in background")


@app.post("/clear")
def clear_db():
    """Drop all indicators from MongoDB for a fresh fetch."""
    count = collection.count_documents({})
    collection.delete_many({})
    logger.info(f"Cleared {count} indicators from DB")
    return {"status": "cleared", "deleted": count}


@app.post("/fetch")
def fetch(limit: int = Query(default=50, ge=10, le=200)):
    global fetch_in_progress
    if fetch_in_progress:
        return {"status": "already_running"}
    Thread(target=_background_fetch, args=(limit,), daemon=True).start()
    return {"status": "started", "limit": limit}


@app.get("/status")
def status():
    return {
        "fetch_in_progress": fetch_in_progress,
        "ml_in_progress":    ml_in_progress,
        "ml_scored_so_far":  ml_progress["scored"],
        "ml_total":          ml_progress["total"],
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
    for doc in docs:
        for key in ("first_seen", "last_seen", "last_abuse_time"):
            val = doc.get(key)
            if hasattr(val, "isoformat"):
                doc[key] = val.isoformat()
    return docs


@app.post("/ml/score")
def ml_score():
    global ml_in_progress, ml_progress
    if ml_in_progress:
        return {"status": "already_running", "progress": ml_progress}
    ml_in_progress = True
    total = collection.count_documents({"enriched": True})
    ml_progress = {"scored": 0, "total": total}
    try:
        count = score_all(collection, progress_cb=_ml_progress_cb)
        return {"status": "done", "scored": count, "total": total}
    finally:
        ml_in_progress = False


@app.get("/ml/score/progress")
def ml_score_progress():
    return {
        "in_progress": ml_in_progress,
        "scored":      ml_progress["scored"],
        "total":       ml_progress["total"],
        "pct":         round(ml_progress["scored"] / max(ml_progress["total"], 1) * 100, 1),
    }


@app.get("/ml/shap/global")
def ml_shap_global():
    return shap_global(n_background=200)


@app.get("/ml/shap/local/{ip}")
def ml_shap_local(ip: str):
    doc = collection.find_one({"indicator": ip}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail=f"IP {ip} not found")
    for key in ("first_seen", "last_seen", "last_abuse_time"):
        val = doc.get(key)
        if hasattr(val, "isoformat"):
            doc[key] = val.isoformat()
    return shap_local(doc)
