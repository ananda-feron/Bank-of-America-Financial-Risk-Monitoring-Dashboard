-- USD values are dollars; ratios and growth are fractions. NULL means unavailable.
SELECT fiscal_year, net_charge_offs, provision_for_credit_losses, allowance_for_credit_losses, net_charge_off_ratio, allowance_to_loans_ratio, net_charge_offs_yoy FROM financial_risk ORDER BY fiscal_year;
