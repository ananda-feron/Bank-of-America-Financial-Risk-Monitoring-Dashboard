-- USD values are dollars; ratios and growth are fractions. NULL means unavailable.
SELECT fiscal_year, cash_and_cash_equivalents, total_deposits, loan_to_deposit_ratio, cash_to_assets_ratio FROM financial_risk ORDER BY fiscal_year;
