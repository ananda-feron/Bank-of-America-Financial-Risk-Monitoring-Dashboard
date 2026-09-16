"""Build a portable SQLite database with uniqueness enforced on both grains."""
import sqlite3
from pathlib import Path

import pandas as pd


def build_database(annual: pd.DataFrame, lineage: pd.DataFrame, destination: Path):
    temporary = destination.with_suffix(".tmp")
    temporary.unlink(missing_ok=True)
    with sqlite3.connect(temporary) as connection:
        annual.to_sql("financial_risk", connection, if_exists="replace", index=False)
        lineage.to_sql("metric_provenance", connection, if_exists="replace", index=False)
        connection.execute("CREATE UNIQUE INDEX annual_year ON financial_risk(fiscal_year)")
        connection.execute("CREATE UNIQUE INDEX metric_year ON metric_provenance(metric, fiscal_year)")
        connection.execute("CREATE VIEW missing_values AS SELECT * FROM metric_provenance WHERE status = 'missing'")
    temporary.replace(destination)
