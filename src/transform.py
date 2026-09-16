"""Normalize reported inputs and calculate ratios without imputing missing facts."""
from __future__ import annotations

import json
import numpy as np
import pandas as pd

# Ratio values are fractions: 0.8 means 80%. Power BI applies percentage formatting.
RATIOS = {
    "loan_to_deposit_ratio": ("total_loans", "total_deposits", False),
    "cash_to_assets_ratio": ("cash_and_cash_equivalents", "total_assets", False),
    "equity_to_assets_ratio": ("total_equity", "total_assets", False),
    "net_charge_off_ratio": ("net_charge_offs", "total_loans", True),
    "allowance_to_loans_ratio": ("loan_loss_allowance", "total_loans", False),
    "trading_asset_exposure": ("trading_assets", "total_assets", False),
    "roa_calculated": ("net_income", "total_assets", True),
    "roe_calculated": ("net_income", "total_equity", True),
    "efficiency_ratio_calculated": ("noninterest_expense", "total_revenue", False),
}
GROWTH_METRICS = ["total_assets", "total_loans", "total_deposits", "net_income",
                  "total_revenue", "net_interest_income", "net_charge_offs",
                  "provision_for_credit_losses", "allowance_for_credit_losses",
                  "common_equity", "trading_assets", "trading_liabilities"]


def safe_divide(numerator, denominator):
    """Return missing when the denominator is nonpositive or an input is missing."""
    numerator, denominator = np.broadcast_arrays(
        np.asarray(numerator, dtype=float), np.asarray(denominator, dtype=float))
    out = np.full(numerator.shape, np.nan)
    valid = np.isfinite(numerator) & np.isfinite(denominator) & (denominator > 0)
    return np.divide(numerator, denominator, out=out, where=valid)


def transform(reported: pd.DataFrame):
    if reported.duplicated(["metric", "fiscal_year"]).any():
        raise ValueError("Duplicate metric/year inputs")
    reported = reported.copy()
    reported["value"] = pd.to_numeric(reported["value"], errors="raise")
    if not set(reported["unit"]).issubset({"USD", "pure"}):
        raise ValueError("Unexpected units; review mapping rather than guessing a scale")
    wide = reported.pivot(index="fiscal_year", columns="metric", values="value").reindex(range(2020, 2026))
    wide.columns.name = None
    lookup = {(r["metric"], int(r["fiscal_year"])): r for r in reported.to_dict("records")}
    derived = []

    def add(metric, values, unit, formula, inputs):
        wide[metric] = values
        for year in wide.index:
            deps = [(name, year + offset) for name, offset in inputs]
            parents = [lookup.get(key) for key in deps]
            value = wide.at[year, metric]
            available = pd.notna(value)
            def combine(field):
                return "|".join(sorted({str(p[field]) for p in parents if p and pd.notna(p.get(field)) and p.get(field) != ""}))
            missing_inputs = [f"{name}:{y}" for (name, y), p in zip(deps, parents)
                              if not p or pd.isna(p.get("value"))]
            row = {
                "metric": metric, "fiscal_year": year, "value": value, "unit": unit,
                "value_type": "calculated", "status": "available" if available else "missing",
                "formula": formula, "input_keys": json.dumps([f"{n}:{y}" for n, y in deps]),
                "missing_reason": "" if available else
                ("Missing inputs: " + ", ".join(missing_inputs) if missing_inputs else "Nonpositive denominator; ratio/change undefined."),
                "source_url": combine("source_url"), "sec_tag": combine("sec_tag"),
                "filing_date": combine("filing_date"), "form_type": combine("form_type"),
                "accession": combine("accession"), "period_end": f"{year}-12-31",
            }
            derived.append(row)
            lookup[(metric, year)] = row

    for name, left, right, sign in [
        ("common_equity", "total_equity", "preferred_equity", -1),
        ("provision_for_credit_losses", "loan_credit_loss_provision", "unfunded_credit_loss_provision", 1),
        ("allowance_for_credit_losses", "loan_loss_allowance", "unfunded_credit_loss_allowance", 1),
    ]:
        add(name, wide[left] + sign * wide[right], "USD",
            f"{left} {'+' if sign == 1 else '-'} {right}", [(left, 0), (right, 0)])

    for metric, (numerator, denominator, average) in RATIOS.items():
        denom = (wide[denominator] + wide[denominator].shift(1)) / 2 if average else wide[denominator]
        inputs = [(numerator, 0), (denominator, 0)]
        if average:
            inputs.append((denominator, -1))
        formula = f"{numerator} / " + (f"mean({denominator}[t-1], {denominator}[t])" if average else denominator)
        add(metric, safe_divide(wide[numerator], denom), "pure", formula, inputs)

    for metric in GROWTH_METRICS:
        # A negative/zero base yields a documented blank, not a misleading growth rate.
        add(metric + "_yoy", safe_divide(wide[metric] - wide[metric].shift(1), wide[metric].shift(1)),
            "pure", f"({metric}[t] - {metric}[t-1]) / {metric}[t-1]",
            [(metric, 0), (metric, -1)])

    lineage = pd.concat([reported.drop(columns=["priority"], errors="ignore"), pd.DataFrame(derived)], ignore_index=True)
    lineage["record_id"] = lineage["metric"] + ":" + lineage["fiscal_year"].astype(str)
    # Keep 2020 inputs in provenance so 2021 average/growth calculations are traceable.
    lineage["is_support_year"] = lineage["fiscal_year"] == 2020
    lineage = lineage.sort_values(["fiscal_year", "metric"]).reset_index(drop=True)
    wide = wide.loc[2021:2025].reset_index()
    return wide, lineage
