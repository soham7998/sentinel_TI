"""
SentinelTI – ML Risk Scoring Engine
Stacking Ensemble: Random Forest + XGBoost → Linear Meta-Learner
SHAP: Global feature importance + Local per-IP explanation
"""

import numpy as np
import logging
from typing import Any

logger = logging.getLogger("ml_model")

FEATURE_NAMES = [
    "abuse_reports",
    "recency_hrs",
    "confidence_pct",
    "vt_detections",
    "vt_total",
    "multi_source",
    "attack_type_count",
    "geo_risk",
    "freshness",
    "source_score",
]

HIGH_RISK_COUNTRIES = {
    "CN", "RU", "KP", "IR", "NG", "RO", "BR", "UA", "IN", "VN"
}


def doc_to_features(doc: dict) -> np.ndarray:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    abuse_reports  = float(doc.get("abuse_reports", 0) or 0)
    confidence_pct = float(doc.get("confidence_score", 0) or 0)
    vt_detections  = float(doc.get("vt_detections", 0) or 0)
    vt_total       = float(doc.get("vt_total", 70) or 70)
    multi_source   = 1.0 if len(doc.get("sources", [])) > 1 else 0.0
    categories     = doc.get("categories", [])
    attack_type_count = float(len(categories)) if isinstance(categories, list) else 0.0
    country        = doc.get("country_code", "") or doc.get("country", "")
    geo_risk       = 1.0 if str(country).upper() in HIGH_RISK_COUNTRIES else 0.0
    source_score   = float(min(doc.get("score", 0) or 0, 10)) / 10.0

    last_abuse = doc.get("last_abuse_time") or doc.get("last_seen")
    if last_abuse:
        if hasattr(last_abuse, "tzinfo"):
            if last_abuse.tzinfo is None:
                last_abuse = last_abuse.replace(tzinfo=timezone.utc)
        elif isinstance(last_abuse, str):
            from dateutil import parser as dtparser
            try:
                last_abuse = dtparser.parse(last_abuse)
                if last_abuse.tzinfo is None:
                    last_abuse = last_abuse.replace(tzinfo=timezone.utc)
            except Exception:
                last_abuse = now
        recency_hrs = max(0.0, (now - last_abuse).total_seconds() / 3600)
    else:
        recency_hrs = 720.0

    freshness = float(np.clip(1.0 - recency_hrs / 720.0, 0.0, 1.0))

    return np.array([
        abuse_reports, recency_hrs, confidence_pct,
        vt_detections, vt_total, multi_source,
        attack_type_count, geo_risk, freshness, source_score,
    ], dtype=np.float32)


def _generate_training_data(n_samples: int = 2000):
    rng = np.random.RandomState(42)
    X_list, y_list = [], []
    for _ in range(n_samples):
        label = rng.randint(0, 2)
        if label == 1:
            row = [
                rng.randint(5, 500), rng.uniform(0, 72), rng.uniform(50, 100),
                rng.randint(3, 40), rng.randint(50, 90),
                rng.choice([0, 1], p=[0.2, 0.8]), rng.randint(1, 8),
                rng.choice([0, 1], p=[0.4, 0.6]),
                rng.uniform(0.6, 1.0), rng.uniform(0.5, 1.0),
            ]
        else:
            row = [
                rng.randint(0, 5), rng.uniform(72, 720), rng.uniform(0, 30),
                rng.randint(0, 2), rng.randint(50, 90),
                rng.choice([0, 1], p=[0.8, 0.2]), rng.randint(0, 2),
                rng.choice([0, 1], p=[0.7, 0.3]),
                rng.uniform(0.0, 0.4), rng.uniform(0.0, 0.4),
            ]
        X_list.append(row)
        y_list.append(label)
    return np.array(X_list, dtype=np.float32), np.array(y_list)


_model_cache: dict[str, Any] = {}


def _train_stacking_model():
    if _model_cache:
        return _model_cache

    from sklearn.ensemble import RandomForestClassifier, StackingClassifier
    from sklearn.linear_model import LogisticRegression
    from xgboost import XGBClassifier

    logger.info("Training stacking ensemble (RF + XGBoost)...")
    X, y = _generate_training_data(2000)

    rf  = RandomForestClassifier(n_estimators=150, max_depth=8, random_state=42, n_jobs=-1)
    xgb = XGBClassifier(
        n_estimators=150, max_depth=6, learning_rate=0.05,
        eval_metric="logloss", random_state=42, verbosity=0
    )
    meta = LogisticRegression(max_iter=500)

    stacking = StackingClassifier(
        estimators=[("rf", rf), ("xgb", xgb)],
        final_estimator=meta,
        passthrough=False, cv=5,
        stack_method="predict_proba", n_jobs=-1
    )
    stacking.fit(X, y)
    logger.info("Stacking ensemble trained ✓")

    _model_cache["model"]   = stacking
    _model_cache["rf"]      = stacking.named_estimators_["rf"]
    _model_cache["xgb"]     = stacking.named_estimators_["xgb"]
    _model_cache["X_train"] = X
    _model_cache["y_train"] = y
    return _model_cache


def get_model():
    return _train_stacking_model()


def score_document(doc: dict) -> dict:
    cache    = get_model()
    x        = doc_to_features(doc).reshape(1, -1)
    prob     = float(cache["model"].predict_proba(x)[0][1])
    rf_prob  = float(cache["rf"].predict_proba(x)[0][1])
    xgb_prob = float(cache["xgb"].predict_proba(x)[0][1])

    if prob >= 0.7:   risk_label = "HIGH"
    elif prob >= 0.3: risk_label = "MEDIUM"
    else:             risk_label = "LOW"

    return {
        "risk_score": round(prob, 4),
        "risk_label": risk_label,
        "rf_prob":    round(rf_prob, 4),
        "xgb_prob":   round(xgb_prob, 4),
        "features":   dict(zip(FEATURE_NAMES, doc_to_features(doc).tolist())),
    }


def score_all(collection, progress_cb=None) -> int:
    cache = get_model()
    count = 0
    total = collection.count_documents({"enriched": True})
    for doc in collection.find({"enriched": True}):
        try:
            result = score_document(doc)
            collection.update_one(
                {"indicator": doc["indicator"]},
                {"$set": {
                    "ml_score":    result["risk_score"],
                    "ml_risk":     result["risk_label"],
                    "rf_prob":     result["rf_prob"],
                    "xgb_prob":    result["xgb_prob"],
                    "ml_features": result["features"],
                    "ml_scored":   True,
                }}
            )
            count += 1
            if progress_cb:
                progress_cb(count, total)
        except Exception as e:
            logger.warning(f"Score failed for {doc.get('indicator')}: {e}")
    logger.info(f"ML scored {count} indicators")
    return count


# ── SHAP – version-safe extraction ────────────────────────────────────────────

def _extract_shap_class1(shap_values, n_features: int) -> np.ndarray:
    """
    Handle all shap_values shapes across shap versions:
      - list of 2 arrays (old):  shap_values[1]  shape (n, f)
      - single 3D array (new):   shap_values[:, :, 1]  shape (n, f, 2)
      - single 2D array:         shap_values  shape (n, f)
    """
    if isinstance(shap_values, list):
        # Old shap: list[class0_array, class1_array]
        sv = np.array(shap_values[1])
    else:
        sv = np.array(shap_values)
        if sv.ndim == 3:
            # New shap: shape (n_samples, n_features, n_classes)
            sv = sv[:, :, 1]
        # else 2D regression-style — use as-is

    # Ensure 2D
    if sv.ndim == 1:
        sv = sv.reshape(1, -1)
    return sv


def shap_global(n_background: int = 200) -> dict:
    try:
        import shap
    except ImportError:
        return {"error": "shap not installed"}

    try:
        cache = get_model()
        rf    = cache["rf"]
        X     = cache["X_train"][:n_background]

        explainer   = shap.TreeExplainer(rf)
        shap_values = explainer.shap_values(X)
        sv          = _extract_shap_class1(shap_values, len(FEATURE_NAMES))

        mean_abs = np.abs(sv).mean(axis=0)
        total    = mean_abs.sum()

        importance = [
            {
                "feature":    FEATURE_NAMES[i],
                "importance": round(float(mean_abs.flat[i]), 5),
                "pct":        round(float(mean_abs.flat[i] / float(total) * 100), 2) if total > 0 else 0,
            }
            for i in range(len(FEATURE_NAMES))
        ]
        importance.sort(key=lambda d: d["importance"], reverse=True)
        return {"global_shap": importance}

    except Exception as e:
        logger.error(f"SHAP global error: {e}", exc_info=True)
        return {"error": str(e)}


def shap_local(doc: dict) -> dict:
    try:
        import shap
    except ImportError:
        return {"error": "shap not installed"}

    try:
        cache = get_model()
        rf    = cache["rf"]
        X_bg  = cache["X_train"][:100]
        x     = doc_to_features(doc).reshape(1, -1)

        explainer   = shap.TreeExplainer(rf, X_bg)
        shap_values = explainer.shap_values(x)
        sv          = _extract_shap_class1(shap_values, len(FEATURE_NAMES))
        sv_row      = sv[0]  # single sample

        features = doc_to_features(doc).tolist()
        result   = []
        for i, name in enumerate(FEATURE_NAMES):
            result.append({
                "feature":    name,
                "value":      round(features[i], 4),
                "shap_value": round(float(np.array(sv_row[i]).flat[0]), 5),
                "direction":  "increases_risk" if sv_row[i] > 0 else "decreases_risk",
            })
        result.sort(key=lambda d: abs(d["shap_value"]), reverse=True)

        exp_val    = explainer.expected_value
        base_value = float(exp_val[1]) if isinstance(exp_val, (list, np.ndarray)) else float(exp_val)

        return {
            "indicator":  doc.get("indicator", ""),
            "risk_score": score_document(doc)["risk_score"],
            "base_value": round(base_value, 5),
            "local_shap": result,
        }

    except Exception as e:
        logger.error(f"SHAP local error: {e}", exc_info=True)
        return {"error": str(e)}
