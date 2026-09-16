# Power BI implementation guide

Build four report pages from the delivered CSVs. This package contains a data model specification, DAX, Power Query example and theme; it does not contain a `.pbix` file.

## Import and model

1. In Power BI Desktop, choose **Get data → Text/CSV** and select `data/processed/financial_risk_annual.csv`. Name the table `FinancialRisk`.
2. Set `fiscal_year` to Whole number. All other columns are Decimal number; do not let entirely blank columns remain Text. Empty CSV cells must become null, never zero. Use `import_query.pq` as a reproducible alternative; replace its file path.
3. Import `metric_provenance.csv` as `MetricProvenance`, and `missing_values.csv` as `MissingValues`. In Power Query, filter both to fiscal_year 2021–2025 for dashboard use. Keep the full source CSVs for 2020 lineage. Set year to Whole number, value to Decimal number, and source fields to Text. `filing_date` in derived rows can contain multiple dates separated by `|`, so retain it as Text.
4. Create `DimYear` with the DAX in `measures.dax`. Add relationships `DimYear[fiscal_year]` (1) → `FinancialRisk[fiscal_year]` (*), → `MetricProvenance[fiscal_year]` (*) and → `MissingValues[fiscal_year]` (*). Use single-direction filtering from DimYear. If Desktop chooses 1:1 for FinancialRisk, set the intended 1:* relationship explicitly. Do not relate the fact tables directly.
5. Hide raw ratio columns from casual aggregation or set them to **Don't summarize**. Disable automatic date/time for this annual model. Use DimYear for axes and slicers. Never sum year-end balance sheets across years.
6. Add the explicit measures from `measures.dax`. Each KPI requires one year in filter context. A single-select year slicer controls detail pages; trend pages use year on the axis and the slicer's visual interaction disabled for charts that should show all five years.

No calculated FinancialRisk columns are required: Python already owns calculations and provenance. `Year Label` is an optional display column on DimYear, sorted by fiscal_year. Avoid recomputing an alternative ratio in a calculated column and drifting from the audited dataset.

## Formatting and shared layout

Use a 16:9 canvas (1280 × 720), 32px outside margins, a 56px header and a 52px filter row. Place four KPI cards across the next row, then two visuals across the main area. Use Segoe UI, 24pt page titles, 12pt labels and 10–11pt table text. Import `theme.json`. Navy is the primary series; blue and teal distinguish comparisons. Red is reserved for explicitly adverse movements, not every negative value.

Format dollar card measures in USD billions with one decimal; label axes “USD billions.” Format ratios as `0.00%` and YoY as `+0.0%;-0.0%;0.0%`. Raw values remain dollars/fractions; do not multiply by 100 before percentage formatting. Show a missing-data label in adjacent text/cards instead of coercing blank to zero. Slicer years are 2021–2025, sorted ascending; default detail year is 2025.

Add a footer: “Bank of America annual disclosures · Filing cutoff 2026-09-16 · Calculated returns use two-point average balances.” Add tooltip fields for unit, definition, calculation basis, filing date and source URL. For URLs containing `|`, use the provenance table for copy/review rather than a single clickable hyperlink.

## Page 1 — Overview and profitability

- Four cards: Total Assets USD bn, Total Revenue USD bn, Net Income USD bn, Calculated ROA.
- Left: line chart, fiscal_year on X, Revenue USD bn and Net Income USD bn on Y. Disable the single-year slicer's interaction with this chart so all five years remain visible.
- Right: line chart of Calculated ROA and Calculated ROE by year; clearly label the differing denominators in tooltips.
- Bottom strip/table: fiscal_year, revenue YoY, net income YoY and calculated efficiency. Negative growth is highlighted for review, not automatically classified as a risk event.
- Slicers: single year for cards; optional metric selection on the provenance tooltip/table.

## Page 2 — Credit risk

- Four cards: Loans USD bn, Net Charge-offs USD bn, Total Provision USD bn and Funded Allowance/Loans.
- Left: clustered columns for net charge-offs and provision by year. Preserve negative provision in 2021 with the zero line visible.
- Right: line chart of approximate net charge-off ratio and funded allowance/loans. Leave a gap in 2021 net charge-off ratio; tooltip explains the missing 2020 loan denominator.
- Detail table: fiscal_year, funded allowance, unfunded allowance, total allowance and net charge-off YoY.
- Slicer: single year for cards, full range for trends. Do not color a provision reserve release as automatically good or bad.

## Page 3 — Liquidity and capital

- Four cards: Deposits USD bn, Loan/Deposit, Cash/Assets and Total Equity/Assets.
- Left: loans and deposits by fiscal year (clustered columns or lines).
- Right: cash/assets and equity/assets trends, labeled as balance-sheet indicators.
- Bottom: capital table with common equity, RWA, CET1, Tier 1, total capital and leverage. Show the **Regulatory Data Status** measure nearby. Missing regulatory data must be conspicuous and must not appear as 0.00%.
- Slicer: single year. Tooltip distinguishes total-equity leverage from regulatory capital adequacy. Add note: “Regulatory ratios require annual-report extraction.”

## Page 4 — Market exposure and data quality

- Four cards: Trading Assets USD bn, Trading Liabilities USD bn, Trading Asset Exposure and Missing Metric Cells.
- Left: trading assets/liabilities trends. Right: trading assets as share of total assets.
- Bottom: provenance table with fiscal_year, metric, value_type, status, missing_reason, sec_tag, filing_date and source_url. Use filters for metric and reported/calculated status.
- Add drillthrough on fiscal_year to this page. Include a table of MissingValues with explanation and formula. Show the missing count for the selected year; selecting all years should show the total 48 missing metric/year cells.
- Caption: “Trading account balances exclude separately reported derivatives; exposure is not VaR.”

## Interaction and acceptance checks

- At 2025, Assets = $3,411.7bn; Loans = $1,185.7bn; Deposits = $2,018.7bn; Net income = $30.5bn.
- Loan/deposit is about 58.73%, cash/assets 6.80%, total equity/assets 8.89%, trading exposure 10.76%.
- Calculated ROA is about 0.91%; calculated total-equity ROE about 10.22%. Do not label these as reported ratios.
- At 2021, the approximate net charge-off ratio is blank, while net charge-offs remain available. At 2022, provision YoY is blank because the prior base was negative.
- Verify year filters reach all three fact tables; clear the slicer to verify multi-year KPI cards remain blank rather than summing balance sheets. Trend measures evaluate once per year-axis point.
- Verify missing regulatory ratios remain blank and the status text is visible. No blank may be converted to zero by DAX, Power Query, or visual settings.
- Compare the provenance table to `metric_provenance.csv`, inspect source links, and check that charts are legible without clipped labels.

These steps require Power BI Desktop for final import, visual construction and interaction testing.
