"""Offline regression tests, including SEC period selection and missing-data safety."""
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.collect import eligible, extract, validate_payload
from src.pipeline import ROOT, run
from src.transform import RATIOS, safe_divide, transform


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    import shutil
    root = tmp_path_factory.mktemp("boa")
    shutil.copytree(ROOT / "config", root / "config")
    (root / "data/raw").mkdir(parents=True)
    for name in ["companyfacts.json", "companyfacts.manifest.json"]:
        shutil.copyfile(ROOT / "data/raw" / name, root / "data/raw" / name)
    summary = run(root)
    annual = pd.read_csv(root / "data/processed/financial_risk_annual.csv")
    lineage = pd.read_csv(root / "data/processed/metric_provenance.csv")
    return root, annual, lineage, summary


def test_required_columns_and_years(built):
    _, annual, lineage, _ = built
    required = {"total_assets", "total_loans", "total_deposits", "net_income", "total_revenue",
                "provision_for_credit_losses", "allowance_for_credit_losses", "common_equity",
                "cet1_ratio", "risk_weighted_assets", *RATIOS}
    assert required <= set(annual)
    assert annual.fiscal_year.tolist() == list(range(2021, 2026))
    assert not annual.fiscal_year.duplicated().any()
    assert not lineage.duplicated(["metric", "fiscal_year"]).any()


def test_numeric_columns_and_finite_values(built):
    for col in built[1]:
        assert pd.api.types.is_numeric_dtype(built[1][col]), col
        assert np.isfinite(built[1][col].dropna()).all(), col


def test_missing_values_are_documented(built):
    _, annual, lineage, _ = built
    by_key = lineage.set_index(["metric", "fiscal_year"])
    for row in annual.to_dict("records"):
        for metric, value in row.items():
            if metric != "fiscal_year" and pd.isna(value):
                source = by_key.loc[(metric, int(row["fiscal_year"]))]
                assert source.status == "missing"
                assert isinstance(source.missing_reason, str) and source.missing_reason.strip()
    assert lineage.loc[lineage.value.isna(), "status"].eq("missing").all()


def test_source_lineage_complete(built):
    lineage = built[2]
    reported = lineage[(lineage.value_type == "reported") & lineage.value.notna()]
    for field in ["sec_tag", "filing_date", "form_type", "source_url", "unit", "accession"]:
        assert reported[field].notna().all(), field
    keys = set(lineage.record_id)
    for row in lineage[(lineage.value_type == "calculated") & lineage.value.notna()].itertuples():
        assert set(json.loads(row.input_keys)) <= keys
        assert pd.notna(row.formula) and pd.notna(row.source_url)


@pytest.mark.parametrize("metric", list(RATIOS))
def test_ratio_formulas_against_inputs(built, metric):
    _, annual, lineage, _ = built
    inputs = lineage.pivot(index="fiscal_year", columns="metric", values="value")
    num, den, average = RATIOS[metric]
    for row in annual.itertuples(index=False):
        y = row.fiscal_year
        denominator = inputs.loc[y, den]
        if average:
            denominator = (denominator + inputs.loc[y - 1, den]) / 2
        expected = inputs.loc[y, num] / denominator if denominator > 0 else np.nan
        assert np.isclose(getattr(row, metric), expected, equal_nan=True)


def test_known_ratio_and_divide_edge_cases():
    assert safe_divide(800, 1000).item() == 0.8
    assert np.isnan(safe_divide(1, 0))
    assert np.isnan(safe_divide(1, -1))
    assert np.isnan(safe_divide(np.nan, 10))
    assert safe_divide(-1, 10).item() == -0.1


def test_reasonable_percentage_ranges(built):
    # Sanity bounds for this bank's historical data, not regulatory limits.
    bounds = {
        "loan_to_deposit_ratio": (0, 2), "cash_to_assets_ratio": (0, 1),
        "equity_to_assets_ratio": (0, 1), "allowance_to_loans_ratio": (0, 1),
        "trading_asset_exposure": (0, 1), "net_charge_off_ratio": (-0.1, 0.2),
        "roa_calculated": (-0.2, 0.2), "roe_calculated": (-1, 1),
        "efficiency_ratio_calculated": (0, 2),
    }
    for metric, (low, high) in bounds.items():
        assert built[1][metric].dropna().between(low, high).all(), metric


def test_2025_statement_reconciliation(built):
    # Independent controls transcribed from 2025 10-K consolidated statements
    # and allowance table. Source and table recorded in docs/validation.md.
    row = built[1].set_index("fiscal_year").loc[2025]
    expected_millions = {
        "total_assets": 3411738, "total_loans": 1185700, "total_deposits": 2018729,
        "cash_and_cash_equivalents": 231845, "net_income": 30509, "total_revenue": 113097,
        "provision_for_credit_losses": 5675, "allowance_for_credit_losses": 14380,
        "net_charge_offs": 5631, "trading_assets": 366954,
    }
    for metric, millions in expected_millions.items():
        assert row[metric] == millions * 1_000_000, metric


def test_negative_base_and_missing_prior_not_imputed(built):
    annual = built[1].set_index("fiscal_year")
    assert pd.isna(annual.loc[2022, "provision_for_credit_losses_yoy"])
    assert pd.isna(annual.loc[2021, "net_charge_off_ratio"])
    assert pd.isna(annual.loc[2021, "total_loans_yoy"])
    assert annual.loc[2021, "provision_for_credit_losses"] < 0


def test_yoy_changes_against_prior_year(built):
    from src.transform import GROWTH_METRICS
    inputs = built[2].pivot(index="fiscal_year", columns="metric", values="value")
    for year in range(2021, 2026):
        for metric in GROWTH_METRICS:
            current, prior = inputs.loc[year, metric], inputs.loc[year - 1, metric]
            expected = (current - prior) / prior if prior > 0 else np.nan
            assert np.isclose(inputs.loc[year, metric + "_yoy"], expected, equal_nan=True)


def test_fetch_stores_exact_payload_and_checksum(tmp_path, monkeypatch):
    import hashlib
    from src.collect import fetch_companyfacts
    payload = tiny_payload([100])
    data = json.dumps(payload).encode()
    class Response:
        status_code = 200
        content = data
        def json(self): return payload
        def raise_for_status(self): pass
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()
    monkeypatch.setattr("src.collect.requests.get", get)
    destination = tmp_path / "companyfacts.json"
    fetch_companyfacts(destination, "Unit test test@example.com")
    assert destination.read_bytes() == data
    manifest = json.loads(destination.with_suffix(".manifest.json").read_text())
    assert manifest["sha256"] == hashlib.sha256(data).hexdigest()
    assert len(calls) == 1 and calls[0][1]["timeout"] == 60


def test_annual_period_selection():
    base = dict(form="10-K", filed="2026-02-25", start="2025-01-01", end="2025-12-31", fy=2026)
    assert eligible(base, 2025, "duration", "2026-09-16")
    assert not eligible({**base, "start": "2025-10-01"}, 2025, "duration", "2026-09-16")
    assert not eligible({**base, "form": "10-Q"}, 2025, "duration", "2026-09-16")
    assert not eligible(base, 2025, "duration", "2026-01-01")
    assert not eligible(base, 2025, "instant", "2026-09-16")


def tiny_payload(values):
    facts = [dict(end="2025-12-31", val=value, accn="0000070858-26-000157", filed="2026-02-25", form="10-K", fy=2025) for value in values]
    return dict(cik=70858, facts={"us-gaap": {"Assets": {"units": {"USD": facts}}}})


def test_conflicting_facts_fail_closed():
    mapping = [dict(metric="assets", tags=["us-gaap:Assets"], unit="USD", period="instant", definition="Assets")]
    with pytest.raises(ValueError, match="Conflicting"):
        extract(tiny_payload([100, 200]), mapping, "2026-09-16")
    _, selected, _ = extract(tiny_payload([100, 100]), mapping, "2026-09-16")
    assert selected.loc[selected.fiscal_year == 2025, "value"].item() == 100


def test_latest_filing_selected_and_as_of_honored():
    payload = tiny_payload([100])
    payload["facts"]["us-gaap"]["Assets"]["units"]["USD"].append(
        dict(end="2025-12-31", val=110, accn="0000070858-26-000158", filed="2026-03-01", form="10-K/A", fy=2025))
    mapping = [dict(metric="assets", tags=["us-gaap:Assets"], unit="USD", period="instant", definition="Assets")]
    for cutoff, value in [("2026-02-28", 100), ("2026-09-16", 110)]:
        _, selected, _ = extract(payload, mapping, cutoff)
        assert selected.loc[selected.fiscal_year == 2025, "value"].item() == value


def test_duplicate_input_rejected(built):
    inputs = pd.read_csv(built[0] / "data/raw/selected_facts.csv")
    with pytest.raises(ValueError, match="Duplicate"):
        transform(pd.concat([inputs, inputs.iloc[[0]]]))


def test_wrong_company_rejected():
    with pytest.raises(ValueError, match="Unexpected SEC"):
        validate_payload({"cik": 1, "facts": {"us-gaap": {}}})


@pytest.mark.parametrize("query_path", sorted((ROOT / "sql").glob("*.sql")), ids=lambda p: p.stem)
def test_sql_queries_execute(built, query_path):
    with sqlite3.connect(built[0] / "data/processed/financial_risk.sqlite") as connection:
        result = connection.execute(query_path.read_text()).fetchall()
        assert result
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_database_matches_csv(built):
    with sqlite3.connect(built[0] / "data/processed/financial_risk.sqlite") as connection:
        annual = pd.read_sql_query("SELECT * FROM financial_risk ORDER BY fiscal_year", connection)
        annual = annual.apply(pd.to_numeric, errors="raise")
        pd.testing.assert_frame_equal(annual, built[1], check_dtype=False)


def test_outputs_reproducible(built):
    path = built[0] / "data/processed/financial_risk_annual.csv"
    before = path.read_bytes()
    run(built[0])
    assert path.read_bytes() == before
