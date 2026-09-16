# Bank of America Financial-Risk Monitoring Dashboard

A reproducible portfolio project analyzing Bank of America Corporation's 2021–2025 annual disclosures with Python, Pandas, NumPy, SQLite, SQL, Pytest and Power BI. Repository slug: `boa-financial-risk-dashboard`.

The project produces five annual observations, a Power BI/Excel-ready CSV, an auditable long-form metric table, a SQLite database, eight SQL analyses and a four-page Power BI implementation guide. It includes real SEC data and runs offline from the checked-in snapshot. Power BI materials are implementation instructions and DAX; a native `.pbix` report is not included.

## Quick start

Use Python 3.11 or newer. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m src.pipeline
python -m pytest -q
```

The default run uses the included snapshot and a filing cutoff of **September 16, 2026**. To refresh, identify your project and real contact email to the SEC:

```bash
export SEC_USER_AGENT="Your project name your-real-email@your-domain.com"
python -m src.pipeline --refresh --as-of 2026-09-16
```

On PowerShell, set `$env:SEC_USER_AGENT = "Your project name your-real-email@your-domain.com"` instead. A refresh replaces the local raw snapshot and derived outputs; use Git to retain earlier versions. Downloading needs internet access, but normal processing and tests do not. A blocked SEC request raises an error rather than substituting example data.

## Project structure

```text
config/metric_mapping.json       Reviewed metric definitions and candidate SEC tags
data/raw/                       SEC JSON, checksum manifest, all annual candidates, selected inputs
data/processed/                 Annual CSV, provenance, missing values, coverage, SQLite database
src/                            Collection, transformation, database and CLI modules
sql/                            Eight standalone analytical queries
notebooks/annual_risk_review.ipynb Optional exploration notebook
tests/                          Offline selection, formula, data-quality and SQL tests
powerbi/                        Model/page guide, DAX, theme and import query
docs/                           Source inspection, methodology and validation notes
```

## Data sources and provenance

- [SEC Company Facts, CIK 0000070858](https://data.sec.gov/api/xbrl/companyfacts/CIK0000070858.json): the raw snapshot contains the SEC response unchanged. A SHA-256 checksum and retrieval timestamp are in its manifest.
- [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces): explains standard-taxonomy/entity-wide coverage and units.
- [2025 Form 10-K filing index](https://www.sec.gov/Archives/edgar/data/70858/000007085826000157/0000070858-26-000157-index.html): verifies the CIK, filing date, accession and registrant.
- [2025 annual filing on the issuer website](https://investor.bankofamerica.com/regulatory-and-other-filings/select-sec-filings/content/0000070858-26-000157/bac-20251231.htm): used to review labels, credit-loss component scope and independent control totals.

Every selected input records metric, SEC tag, filing date, fiscal year, original filing fiscal year, form, period dates, accession, source URL, unit and reported/calculated status. Calculated records contain their formula and parent metric/year identifiers. The long-form table retains support-year records so calculations can be traced recursively.

The downloaded API metadata unexpectedly labels CIK 70858 as “BofA Finance LLC.” The raw label is preserved, not silently corrected. The SEC filing index identifies Bank of America Corporation, and the 2025 statement controls reconcile to the extracted data. Review this discrepancy on future refreshes.

## Methodology and metrics

1. Verify candidate tag presence and units at runtime; save the audit in `tag_audit.csv`. Similar tag names are not treated as proof of equivalent meaning.
2. Accept only 10-K/10-K/A facts ending December 31. Income and flow facts must start January 1 of the same year. A comparative fact's `fy` may refer to a later filing year, so the fiscal observation year comes from the period dates.
3. Prefer the reviewed current tag, then its listed legacy equivalent; within that tag choose the latest filing available at the cutoff. This produces a latest-disclosed series, not a point-in-time backtest. Conflicting values within the selected accession stop the pipeline.
4. Store USD amounts as dollars, not millions; XBRL API values already incorporate scale. Store ratios and changes as fractions (0.8 = 80%). No forward fill, interpolation or zero substitution is used.
5. Calculate common equity as total equity minus preferred carrying value. Total credit-loss allowance and provision combine funded loan/lease and unfunded commitment components. Each remains marked calculated.
6. Calculate loan/deposit, cash/assets, total equity/assets, funded allowance/loans and trading assets/assets using year-end balances. Calculate ROA, total-equity ROE and net charge-off ratios using the mean of prior and current year-end balances. These are approximations, not the bank's reported daily-average ratios.
7. Calculate GAAP efficiency as noninterest expense / revenue net of interest expense. Calculate YoY as `(current - prior) / prior`, with a documented blank for missing or nonpositive prior values.

See [methodology](docs/methodology.md) and [source inspection](docs/source_inspection.md) for definitions and extraction limitations.

## Data coverage and limitations

The snapshot supplies **17 reported input metrics for each of five years (85 values)**. Nine requested reported metrics remain blank: RWA, NIM, reported ROA/ROE, CET1, Tier 1 capital, total capital, Tier 1 leverage and reported efficiency. Their required custom or dimensional contexts are unavailable in Company Facts. The manual extraction guide identifies annual-report tables and required reporting bases.

The current mapping has no eligible 2020 gross-loan observation. Consequently 2021 loan growth and the 2021 approximate net charge-off ratio are blank. The 2022 provision growth rate is also blank because its 2021 base is negative. In total, there are **48 missing metric/year cells** in the 2021–2025 analytical dataset, each documented in `missing_values.csv`.

Cash uses the issuer's cash-and-equivalents label on a broader restricted-cash taxonomy concept. It is not a measure of immediately deployable liquidity. Trading exposure excludes separately reported derivatives and is not VaR, stress loss or a complete market-risk measure. Equity/assets is a book-capital ratio, not CET1. Annual data obscures intra-year volatility; this is historical portfolio research, not a regulatory risk model.

## SQL, Power BI and Excel

SQLite tables are `financial_risk` (one row per year) and `metric_provenance` (one row per metric/year). Unique indexes enforce those grains. `missing_values` is a database view. Execute any file in `sql/` with SQLite or a database viewer. For example:

```bash
sqlite3 data/processed/financial_risk.sqlite < sql/03_liquidity.sql
```

Import `data/processed/financial_risk_annual.csv` into Power BI as `FinancialRisk`. Follow [the implementation guide](powerbi/implementation_guide.md), then apply [DAX measures](powerbi/measures.dax) and `theme.json`. CSVs can also be opened in Excel through **Data → From Text/CSV**; set fiscal year to whole number and ratio columns to Percentage. Preserve blanks and avoid rounding source USD values.

The optional notebook requires Jupyter, which is not needed by the pipeline. Install it separately if desired (`python -m pip install jupyter`) and open the notebook from the repository root.

## Validation and reproducibility

Tests cover required columns, numeric types, year uniqueness, complete missing-value explanations, source lineage, every calculated ratio, denominator edge cases, annual period filters, latest-filing selection, conflicting facts, SQL execution, database/CSV equality and deterministic CSV output. Ten 2025 totals are independently checked against the annual filing. See [validation notes](docs/validation.md).

GitHub Actions runs the offline pipeline and tests on pushes and pull requests. The raw data is public SEC data; no credentials are stored. No remote repository or publication is required to use this project.
