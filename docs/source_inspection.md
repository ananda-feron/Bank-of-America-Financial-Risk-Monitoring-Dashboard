# Source inspection before implementation

Inspected September 16, 2026, before writing the collection/transform modules.

The actual Company Facts response has top-level `cik`, `entityName`, and `facts`. Taxonomy namespaces include `dei`, `invest`, `us-gaap`, and `ffd`. Each concept includes a label/description and `units`, whose arrays hold observations with `val`, `start` where applicable, `end`, `accn`, `fy`, `fp`, `form`, `filed` and sometimes `frame`. Some descriptions are null. The file includes quarterly, annual, comparative and repeated facts; taking the last row or filtering only `fy` would be incorrect.

The SEC [API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) describes coverage restricted to standard-taxonomy entity-wide facts. Custom tags and dimensional facts can exist in the 10-K without appearing in Company Facts.

| Metric group | Verified treatment |
|---|---|
| Assets, deposits, income, revenue, net interest income, equity | Standard tags with 2021–2025 annual observations; see mapping JSON and generated tag audit. |
| Loans and allowance | Current financing-receivable tags exclude accrued interest. Loans are gross of allowance. Funded allowance is distinct from the unfunded commitment reserve. |
| Total provision and allowance | Derived from funded plus unfunded components. The 2025 loan provision of $5.595bn alone is not the total $5.675bn provision. |
| Cash | `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` matches the issuer balance-sheet row “Cash and cash equivalents”; do not infer that every dollar is unrestricted. |
| Trading assets | `TradingSecurities` matches trading account assets. Separately presented derivatives are outside this measure. |
| Common equity | Derived as total parent equity less preferred equity carrying value. |
| Regulatory ratios and RWA | Required consolidated/basis contexts unavailable in the API; manual review of Capital Management/regulatory tables is needed. |
| Reported NIM, ROA, ROE and efficiency | Not available through verified API mappings. Preserve separate fields from calculated approximations. |

The 2025 [filing index](https://www.sec.gov/Archives/edgar/data/70858/000007085826000157/0000070858-26-000157-index.html) confirms accession `0000070858-26-000157`, filing date February 25, 2026, and Bank of America Corporation. This resolves the intended filing identity despite the downloaded API `entityName` anomaly. The raw payload remains unchanged for audit.

## Manual extraction workflow

Use the blank `data/raw/manual_extraction_template.csv`. For each missing metric/year:

1. Open that year's 10-K from the [issuer annual reports](https://investor.bankofamerica.com/regulatory-and-other-filings/annual-reports).
2. Use the table identified in `config/metric_mapping.json`; select consolidated Bank of America Corporation, not a bank subsidiary. For risk-weighted metrics choose and record the standardized approach consistently.
3. Record the actual metric, not its minimum regulatory requirement. Distinguish Tier 1 leverage from supplementary leverage. Record GAAP versus FTE basis for profitability measures.
4. Enter USD dollars or a fraction for a ratio. A disclosed 11.4% becomes 0.114. Record page/table, filing URL/date, tag if present, reviewer and review date.
5. Reconcile to the source and independently review before extending the pipeline. The template is intentionally not automatically ingested; unreviewed entries cannot overwrite SEC facts.

This project does not claim these unavailable values have been manually collected.
