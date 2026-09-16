# Validation

Run `python -m pytest -q` from the repository root. The tests build a fresh database and CSVs in a temporary directory from the included raw snapshot; they do not require SEC access or mutate delivered data.

Verified September 16, 2026 with Python 3.12: **34 tests passed**, all eight SQL queries executed, and all four notebook code cells ran successfully. The SEC download was performed over HTTPS and archived with a checksum. The collector's persistence and provenance behavior is also covered by an isolated HTTP-response test.

Independent 2025 controls (USD millions), transcribed from the [2025 10-K](https://investor.bankofamerica.com/regulatory-and-other-filings/select-sec-filings/content/0000070858-26-000157/bac-20251231.htm):

| Statement/table | Metric | Control |
|---|---|---:|
| Consolidated Balance Sheet | Assets | 3,411,738 |
| Consolidated Balance Sheet | Gross loans and leases | 1,185,700 |
| Consolidated Balance Sheet | Deposits | 2,018,729 |
| Consolidated Balance Sheet | Cash and cash equivalents | 231,845 |
| Consolidated Balance Sheet | Trading account assets | 366,954 |
| Consolidated Statement of Income | Net income | 30,509 |
| Consolidated Statement of Income | Revenue net of interest expense | 113,097 |
| Consolidated Statement of Income | Provision for credit losses | 5,675 |
| Allowance for Credit Losses table | Total allowance including unfunded commitments | 14,380 |
| Allowance for Credit Losses table | Net charge-offs | 5,631 |

Controls are multiplied by 1,000,000 before comparison with XBRL USD values. They verify statement scope and scale independently of the formula implementation.

Tests also cover period selection, comparative `fy` labels, 10-Q rejection, as-of dates, amended filings, conflicts, duplicate inputs, numeric types, missing-value documentation, ratio arithmetic, provenance dependencies, sanity bounds, eight SQL queries, database integrity and repeatability. Percentage sanity bands are analytical checks for this dataset, not supervisory thresholds.

Power BI Desktop is not executed as part of Python validation. DAX and layout files are implementation materials; model import, rendering and interactions must be verified in Desktop using the guide's acceptance checklist.
