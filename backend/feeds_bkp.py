import ipaddress
import logging
import requests
from typing import List, Dict
import geoip2.database

logger = logging.getLogger("feeds")

# -----------------------------
# GEOIP
# -----------------------------
GEOIP_DB = "/app/geoip/GeoLite2-City.mmdb"
geo_reader = None

try:
    geo_reader = geoip2.database.Reader(GEOIP_DB)
    logger.info("GeoIP database loaded")
except Exception as e:
    logger.warning(f"GeoIP load failed: {e}")
    geo_reader = None


def geoip_enrich(ip: str) -> dict:
    if not geo_reader:
        return {}

    try:
        r = geo_reader.city(ip)
        return {
            "country": r.country.name,
            "country_code": r.country.iso_code,
            "state": r.subdivisions.most_specific.name,
            "city": r.city.name,
        }
    except Exception:
        return {}


# -----------------------------
# PARSER
# -----------------------------
def parse_plain_list(text: str, source: str) -> List[Dict]:
    indicators = []

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        token = line.split()[0]

        try:
            ipaddress.ip_address(token)
            doc = {
                "indicator": token,
                "type": "ip",
                "source": source,
                "malicious": True,
                "confidence_score": 80,
            }
            doc.update(geoip_enrich(token))
            indicators.append(doc)
        except ValueError:
            continue

    return indicators


# -----------------------------
# FEEDS
# -----------------------------
def fetch_abuse_ch():
    url = "https://feodotracker.abuse.ch/downloads/ipblocklist.txt"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return parse_plain_list(r.text, "abuse.ch")


def fetch_cins():
    url = "https://cinsscore.com/list/ci-badguys.txt"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return parse_plain_list(r.text, "CINS Army")


# -----------------------------
# AGGREGATOR (CRITICAL)
# -----------------------------
def fetch_all_feeds():
    results = []
    results.extend(fetch_abuse_ch())
    results.extend(fetch_cins())

    seen = set()
    uniq = []

    for r in results:
        if r["indicator"] in seen:
            continue
        seen.add(r["indicator"])
        uniq.append(r)

        if len(uniq) >= 300:
            break

    return uniq

