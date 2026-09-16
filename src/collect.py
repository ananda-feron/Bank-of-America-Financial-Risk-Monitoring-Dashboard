"""Download SEC Company Facts and select comparable annual observations."""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

CIK = 70858
API_URL = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK:010d}.json"


def fetch_companyfacts(destination: Path, user_agent: str | None = None) -> dict:
    """One request, with bounded backoff; identify yourself to SEC on refresh."""
    user_agent = user_agent or os.environ.get("SEC_USER_AGENT", "")
    if "@" not in user_agent:
        raise ValueError("Set SEC_USER_AGENT to your project name and real contact email.")
    for attempt in range(4):
        response = requests.get(API_URL, headers={"User-Agent": user_agent}, timeout=60)
        if response.status_code not in (429, 500, 502, 503, 504):
            break
        if attempt < 3:
            time.sleep(2 ** (attempt + 1))
    response.raise_for_status()
    payload = response.json()
    validate_payload(payload)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    temporary.write_bytes(response.content)
    temporary.replace(destination)
    write_manifest(destination, payload)
    return payload


def validate_payload(payload: dict) -> None:
    if int(payload.get("cik", -1)) != CIK or "us-gaap" not in payload.get("facts", {}):
        raise ValueError("Unexpected SEC company or missing US-GAAP facts.")


def write_manifest(path: Path, payload: dict) -> None:
    manifest = {
        "source_url": API_URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "cik": CIK,
        "api_entity_name": payload.get("entityName"),
        "intended_entity": "Bank of America Corporation",
        "identity_verification": "CIK and 2025 accession verified against SEC filing index; API label retained verbatim.",
        "identity_source": "https://www.sec.gov/Archives/edgar/data/70858/000007085826000157/0000070858-26-000157-index.html",
    }
    path.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def eligible(fact: dict, year: int, period: str, as_of: str) -> bool:
    """Use period dates, not SEC fy (which can describe a later comparative filing)."""
    if fact.get("form") not in ("10-K", "10-K/A"):
        return False
    if fact.get("filed", "9999") > as_of or fact.get("end") != f"{year}-12-31":
        return False
    if period == "instant":
        return not fact.get("start")
    return fact.get("start") == f"{year}-01-01"


def extract(payload: dict, mapping: list[dict], as_of: str):
    """Keep all eligible candidates and a complete selected/missing metric-year grid.

    Preferred tags are reviewed equivalents. Within the preferred available tag,
    the latest filing wins. Conflicting values within one accession fail closed.
    """
    validate_payload(payload)
    rows, selected, audit = [], [], []
    for spec in mapping:
        for namespace, tag in (t.split(":", 1) for t in spec["tags"]):
            concept = payload["facts"].get(namespace, {}).get(tag)
            audit.append({
                "metric": spec["metric"], "sec_tag": f"{namespace}:{tag}",
                "exists": concept is not None,
                "label": (concept or {}).get("label", ""),
                "description": (concept or {}).get("description", ""),
                "available_units": "|".join((concept or {}).get("units", {})),
                "expected_unit": spec["unit"], "definition": spec["definition"],
            })
        for year in range(2020, 2026):
            candidates = []
            for priority, full_tag in enumerate(spec["tags"]):
                namespace, tag = full_tag.split(":", 1)
                concept = payload["facts"].get(namespace, {}).get(tag, {})
                for fact in concept.get("units", {}).get(spec["unit"], []):
                    if not eligible(fact, year, spec["period"], as_of):
                        continue
                    accession = fact["accn"]
                    row = {
                        "metric": spec["metric"], "fiscal_year": year,
                        "value": fact["val"], "unit": spec["unit"],
                        "sec_tag": full_tag, "filing_date": fact["filed"],
                        "filing_fiscal_year": fact.get("fy"), "form_type": fact["form"],
                        "period_start": fact.get("start", ""), "period_end": fact["end"],
                        "accession": accession, "source_url":
                        f"https://www.sec.gov/Archives/edgar/data/{CIK}/{accession.replace('-', '')}/{accession}-index.html",
                        "api_url": API_URL, "value_type": "reported",
                        "status": "available", "missing_reason": "", "priority": priority,
                    }
                    candidates.append(row)
            rows.extend(candidates)
            base = {
                "metric": spec["metric"], "fiscal_year": year, "value": None,
                "unit": spec["unit"], "sec_tag": "", "filing_date": "",
                "filing_fiscal_year": None, "form_type": "", "period_start": "",
                "period_end": f"{year}-12-31", "accession": "", "source_url": "",
                "api_url": API_URL, "value_type": "reported", "status": "missing",
                "missing_reason": spec.get("manual_note") or "No eligible annual fact in the reviewed tags and unit.",
                "priority": None,
            }
            if candidates:
                preferred = min(r["priority"] for r in candidates)
                pool = [r for r in candidates if r["priority"] == preferred]
                last = max((r["filing_date"], r["accession"]) for r in pool)
                pool = [r for r in pool if (r["filing_date"], r["accession"]) == last]
                if len({r["value"] for r in pool}) != 1:
                    raise ValueError(f"Conflicting SEC values: {spec['metric']} {year} {last}")
                base = pool[0].copy()
            selected.append(base)
    return pd.DataFrame(rows), pd.DataFrame(selected), pd.DataFrame(audit)
