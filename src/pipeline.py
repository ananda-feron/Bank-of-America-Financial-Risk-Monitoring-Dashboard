"""Run with python -m src.pipeline; cached data makes the default run offline."""
import argparse
import hashlib
import json
from pathlib import Path

from .collect import extract, fetch_companyfacts
from .database import build_database
from .transform import transform

ROOT = Path(__file__).resolve().parents[1]


def run(root: Path = ROOT, refresh=False, as_of="2026-09-16"):
    raw, processed = root / "data/raw", root / "data/processed"
    raw.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    snapshot = raw / "companyfacts.json"
    if refresh or not snapshot.exists():
        fetch_companyfacts(snapshot)
    payload = json.loads(snapshot.read_text())
    manifest_path = snapshot.with_suffix(".manifest.json")
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest["sha256"] != hashlib.sha256(snapshot.read_bytes()).hexdigest():
            raise ValueError("SEC snapshot checksum mismatch")
    mapping = json.loads((root / "config/metric_mapping.json").read_text())
    candidates, reported, audit = extract(payload, mapping, as_of)
    annual, lineage = transform(reported)
    candidates.to_csv(raw / "annual_facts.csv", index=False)
    reported.to_csv(raw / "selected_facts.csv", index=False)
    audit.to_csv(processed / "tag_audit.csv", index=False)
    annual.to_csv(processed / "financial_risk_annual.csv", index=False)
    lineage.to_csv(processed / "metric_provenance.csv", index=False)
    missing = lineage.loc[lineage.status == "missing"]
    missing.to_csv(processed / "missing_values.csv", index=False)
    coverage = lineage.loc[~lineage.is_support_year].groupby(["metric", "value_type"])["status"].agg(
        available_years=lambda s: int((s == "available").sum()),
        missing_years=lambda s: int((s == "missing").sum())).reset_index()
    coverage.to_csv(processed / "coverage.csv", index=False)
    build_database(annual, lineage, processed / "financial_risk.sqlite")
    summary = {"as_of": as_of, "years": annual.fiscal_year.tolist(),
               "selected_reported_values": int(((reported.fiscal_year >= 2021) & reported.value.notna()).sum()),
               "missing_metric_years": int(((lineage.fiscal_year >= 2021) & (lineage.status == "missing")).sum()),
               "snapshot_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
               "ratio_unit": "fraction; format as percent", "annual_rows": len(annual)}
    (processed / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Download current SEC snapshot (requires SEC_USER_AGENT).")
    parser.add_argument("--as-of", default="2026-09-16", help="Latest permitted filing date, YYYY-MM-DD.")
    args = parser.parse_args()
    from datetime import date
    date.fromisoformat(args.as_of)
    print(json.dumps(run(refresh=args.refresh, as_of=args.as_of), indent=2))


if __name__ == "__main__":
    main()
