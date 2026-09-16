-- USD values are dollars; ratios and growth are fractions. NULL means unavailable.
SELECT fiscal_year, trading_assets, trading_liabilities, trading_asset_exposure, trading_assets_yoy FROM financial_risk ORDER BY fiscal_year;
