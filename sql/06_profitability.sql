-- USD values are dollars; ratios and growth are fractions. NULL means unavailable.
SELECT fiscal_year, total_revenue, net_interest_income, net_income, roa_calculated, roe_calculated, efficiency_ratio_calculated, roa_reported, roe_reported FROM financial_risk ORDER BY fiscal_year;
