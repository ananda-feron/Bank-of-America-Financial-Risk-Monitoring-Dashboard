-- USD values are dollars; ratios and growth are fractions. NULL means unavailable.
SELECT fiscal_year, metric, value AS yoy_change FROM metric_provenance WHERE fiscal_year BETWEEN 2021 AND 2025 AND metric LIKE '%_yoy' AND value < 0 ORDER BY fiscal_year, metric;
