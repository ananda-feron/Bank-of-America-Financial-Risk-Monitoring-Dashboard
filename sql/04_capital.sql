-- USD values are dollars; ratios and growth are fractions. NULL means unavailable.
SELECT fiscal_year, common_equity, total_equity, equity_to_assets_ratio, risk_weighted_assets, cet1_ratio, tier1_capital_ratio, total_capital_ratio, tier1_leverage_ratio FROM financial_risk ORDER BY fiscal_year;
