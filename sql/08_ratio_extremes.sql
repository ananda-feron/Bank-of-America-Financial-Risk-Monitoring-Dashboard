-- USD values are dollars; ratios and growth are fractions. NULL means unavailable.
WITH ratios AS (
 SELECT fiscal_year, metric, value,
        DENSE_RANK() OVER (PARTITION BY metric ORDER BY value) AS low_rank,
        DENSE_RANK() OVER (PARTITION BY metric ORDER BY value DESC) AS high_rank
 FROM metric_provenance
 WHERE fiscal_year BETWEEN 2021 AND 2025 AND unit = 'pure'
   AND metric NOT LIKE '%_yoy' AND value IS NOT NULL
)
SELECT fiscal_year, metric, value,
       CASE WHEN low_rank = 1 AND high_rank = 1 THEN 'both'
            WHEN low_rank = 1 THEN 'lowest' ELSE 'highest' END AS extreme
FROM ratios WHERE low_rank = 1 OR high_rank = 1 ORDER BY metric, fiscal_year;
