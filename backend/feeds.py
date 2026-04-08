"""
SentinelTI – Feed Ingestion & Async Enrichment
Sources: Abuse.ch, CINS Army, OTX AlienVault
Enrichment: VirusTotal (optional), AbuseIPDB (rich), GeoIP + ASN
"""

import os
import ipaddress
import logging
from datetime import datetime, timezone

import requests

logger = logging.getLogger("feeds")

VT_KEY         = os.getenv("VIRUSTOTAL_API_KEY", "")
ABUSEIPDB_KEY  = os.getenv("ABUSEIPDB_API_KEY", "")
OTX_KEY        = os.getenv("OTX_API_KEY", "")

SOURCE_SCORE = {
    "abuse.ch":  5,
    "CINS Army": 2,
    "OTX":        4,
    "VirusTotal": 3,
    "AbuseIPDB":  3,
}


def risk_level(score: float) -> str:
    if score >= 9:
        return "HIGH"
    if score >= 5:
        return "MEDIUM"
    return "LOW"


# ── Feed Parsers ───────────────────────────────────────────────────────────────

def _parse_plain_list(text: str, source: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        token = line.split()[0]
        try:
            ipaddress.ip_address(token)
            out.append({
                "indicator": token,
                "sources":   [source],
                "score":     SOURCE_SCORE[source],
                "risk":      risk_level(SOURCE_SCORE[source]),
            })
        except ValueError:
            continue
    return out


def fetch_abuse_ch() -> list[dict]:
    try:
        r = requests.get(
            "https://feodotracker.abuse.ch/downloads/ipblocklist.txt",
            timeout=15
        )
        r.raise_for_status()
        logger.info(f"Abuse.ch: {len(r.text.splitlines())} lines")
        return _parse_plain_list(r.text, "abuse.ch")
    except Exception as e:
        logger.error(f"Abuse.ch fetch failed: {e}")
        return []


def fetch_cins() -> list[dict]:
    try:
        r = requests.get(
            "https://cinsscore.com/list/ci-badguys.txt",
            timeout=15
        )
        r.raise_for_status()
        logger.info(f"CINS Army: {len(r.text.splitlines())} lines")
        return _parse_plain_list(r.text, "CINS Army")
    except Exception as e:
        logger.error(f"CINS fetch failed: {e}")
        return []



def fetch_otx() -> list[dict]:
    """
    Fetch malicious IPs from OTX AlienVault subscribed pulses.
    Returns up to 500 unique IP indicators with tags and malware families.
    """
    if not OTX_KEY:
        logger.debug("OTX key not set – skipping")
        return []

    headers = {"X-OTX-API-KEY": OTX_KEY}
    seen: set[str] = set()
    out:  list[dict] = []

    try:
        # Get subscribed pulses (most recent 10)
        url  = "https://otx.alienvault.com/api/v1/pulses/subscribed?limit=10&page=1"
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        pulses = resp.json().get("results", [])
        logger.info(f"OTX: {len(pulses)} pulses fetched")

        for pulse in pulses:
            tags    = pulse.get("tags", [])
            name    = pulse.get("name", "")
            for ioc in pulse.get("indicators", []):
                if ioc.get("type") not in ("IPv4", "IPv6"):
                    continue
                ip = ioc.get("indicator", "").strip()
                if not ip or ip in seen:
                    continue
                try:
                    ipaddress.ip_address(ip)
                except ValueError:
                    continue
                seen.add(ip)
                out.append({
                    "indicator": ip,
                    "sources":   ["OTX"],
                    "score":     SOURCE_SCORE["OTX"],
                    "risk":      risk_level(SOURCE_SCORE["OTX"]),
                    "otx_pulse": name,
                    "otx_tags":  tags,
                })

        logger.info(f"OTX: {len(out)} unique IPs extracted")
        return out

    except Exception as e:
        logger.error(f"OTX fetch failed: {e}")
        return []

def fetch_base_indicators(limit: int = 200) -> list[dict]:
    """Merge, deduplicate, and cap at limit."""
    seen: dict[str, dict] = {}

    for ioc in fetch_abuse_ch() + fetch_cins() + fetch_otx():
        ip = ioc["indicator"]
        if ip not in seen:
            seen[ip] = ioc
        else:
            # merge sources, accumulate score
            existing = seen[ip]
            merged_sources = list(set(existing["sources"] + ioc["sources"]))
            merged_score   = min(sum(
                SOURCE_SCORE.get(s, 0) for s in merged_sources
            ), 10)
            seen[ip] = {
                **existing,
                "sources": merged_sources,
                "score":   merged_score,
                "risk":    risk_level(merged_score),
            }

    result = list(seen.values())[:limit]
    logger.info(f"Base indicators after dedup: {len(result)}")
    return result


# ── Enrichment Functions ───────────────────────────────────────────────────────

_vt_consecutive_429 = 0
_VT_MAX_429 = 5   # skip VT for rest of batch after 5 consecutive rate limits

def _enrich_virustotal(ip: str) -> dict:
    """
    Returns dict with vt_detections, vt_total, vt_malicious.
    Gracefully returns empty dict if key missing or rate limited.
    """
    global _vt_consecutive_429
    if not VT_KEY:
        return {}
    if _vt_consecutive_429 >= _VT_MAX_429:
        return {}   # silently skip rest of batch

    import time
    url     = f"https://www.virustotal.com/api/v3/ip_addresses/{ip}"
    headers = {"x-apikey": VT_KEY}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 429:
            _vt_consecutive_429 += 1
            logger.warning(f"VT rate limit ({_vt_consecutive_429}/{_VT_MAX_429}) – pausing 15s")
            time.sleep(15)
            return {}
        _vt_consecutive_429 = 0   # reset on success
        if r.status_code == 404:
            return {"vt_detections": 0, "vt_total": 0, "vt_malicious": False}
        if r.status_code != 200:
            logger.warning(f"VT {ip} → HTTP {r.status_code}")
            return {}
        attrs      = r.json()["data"]["attributes"]
        stats      = attrs.get("last_analysis_stats", {})
        detections = int(stats.get("malicious", 0))
        total      = int(sum(stats.values()))
        return {
            "vt_detections": detections,
            "vt_total":      total,
            "vt_malicious":  detections > 0,
        }
    except Exception as e:
        logger.warning(f"VT enrichment error for {ip}: {e}")
        return {}


def _enrich_abuseipdb(ip: str) -> dict:
    """
    Returns rich dict: abuse_reports, confidence_score, last_abuse_time,
    categories, country_code, isp, domain, is_tor, is_public.
    """
    if not ABUSEIPDB_KEY:
        logger.debug("AbuseIPDB key not set – skipping")
        return {}

    url     = "https://api.abuseipdb.com/api/v2/check"
    headers = {"Key": ABUSEIPDB_KEY, "Accept": "application/json"}
    params  = {"ipAddress": ip, "maxAgeInDays": 90, "verbose": True}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code != 200:
            logger.warning(f"AbuseIPDB {ip} → HTTP {r.status_code}")
            return {}
        d = r.json()["data"]

        # parse last abuse time
        lat_str = d.get("lastReportedAt")
        try:
            from dateutil import parser as dtparser
            last_abuse_time = dtparser.parse(lat_str) if lat_str else None
        except Exception:
            last_abuse_time = None

        # categories: AbuseIPDB returns list of ints
        raw_cats = d.get("reports", [])
        categories = list({
            cat
            for report in raw_cats
            for cat in (report.get("categories") or [])
        })

        return {
            "abuse_reports":    int(d.get("totalReports", 0)),
            "confidence_score": float(d.get("abuseConfidenceScore", 0)),
            "last_abuse_time":  last_abuse_time,
            "categories":       categories,
            "country_code":     d.get("countryCode", ""),
            "isp":              d.get("isp", ""),
            "domain":           d.get("domain", ""),
            "is_tor":           bool(d.get("isTor", False)),
            "is_public":        bool(d.get("isPublic", True)),
            "abuse_malicious":  float(d.get("abuseConfidenceScore", 0)) > 25,
        }
    except Exception as e:
        logger.warning(f"AbuseIPDB enrichment error for {ip}: {e}")
        return {}

# ── Helpers ─────────────────────────────
import pycountry

def country_name(code):
    try:
        return pycountry.countries.get(alpha_2=code).name
    except:
        return code
        
def _enrich_ipinfo(ip: str) -> dict:
    """
    GeoIP enrichment using ipinfo.io (no file, works on Railway)
    Returns: country, country_code, city, lat, lon, isp
    """
    try:
        url = f"https://ipinfo.io/{ip}/json"
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            logger.warning(f"ipinfo {ip} → HTTP {r.status_code}")
            return {}

        d = r.json()

        # location comes as "lat,lon"
        loc = d.get("loc", "")
        lat, lon = None, None
        if loc and "," in loc:
            try:
                lat, lon = map(float, loc.split(","))
            except:
                pass

        return {
            "country": country_name(d.get("country", "")),   # US, CN, etc.
            "country_code": d.get("country", ""),
            "city":         d.get("city", ""),
            "latitude":     lat,
            "longitude":    lon,
            "isp":          d.get("org", ""),
        }

    except Exception as e:
        logger.warning(f"ipinfo enrichment error for {ip}: {e}")
        return {}


# ── Background Enrichment Pipeline ────────────────────────────────────────────

def enrich_indicators(collection) -> None:
    """
    Async background enrichment. For each unenriched IOC:
    1. GeoIP + ASN
    2. AbuseIPDB (full rich data)
    3. VirusTotal (optional – skipped if no key)
    Then updates MongoDB with enriched fields.
    """
    logger.info("Background enrichment started")
    total = collection.count_documents({"enriched": False})
    done  = 0

    for doc in collection.find({"enriched": False}):
        ip      = doc["indicator"]
        sources = set(doc.get("sources", []))
        score   = float(doc.get("score", 0))
        update  = {}

        # 1. GeoIP
        geo = _enrich_ipinfo(ip)
        update.update(geo)

        # 2. AbuseIPDB
        abuse = _enrich_abuseipdb(ip)
        update.update(abuse)
        if abuse.get("abuse_malicious"):
            sources.add("AbuseIPDB")
            score = min(score + SOURCE_SCORE["AbuseIPDB"], 10)

        # 3. VirusTotal (graceful skip)
        vt = _enrich_virustotal(ip)
        update.update(vt)
        if vt.get("vt_malicious"):
            sources.add("VirusTotal")
            score = min(score + SOURCE_SCORE["VirusTotal"], 10)

        # Recalculate multi_source flag
        update["multi_source"] = len(sources) > 1

        update["sources"]  = list(sources)
        update["score"]    = round(score, 2)
        update["risk"]     = risk_level(score)
        update["last_seen"] = datetime.now(timezone.utc)
        update["enriched"] = True

        collection.update_one(
            {"indicator": ip},
            {"$set": update}
        )
        done += 1
        if done % 10 == 0:
            logger.info(f"Enriched {done}/{total}")

    logger.info(f"Enrichment complete: {done} indicators processed")
