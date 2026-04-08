# Industry Expectations

What fields should/shouldn't be populated, and what metric ranges are normal,
per industry category. Claude commands read this to avoid false-positive anomalies.

## Field Expectations by Industry

| Field             | Tech | Banks | REITs | Defense | Consumer | Energy | Utilities | Healthcare | SaaS |
|-------------------|------|-------|-------|---------|----------|--------|-----------|------------|------|
| revenue           | YES  | YES   | YES   | YES     | YES      | YES    | YES       | YES        | YES  |
| cogs              | YES  | maybe | maybe | YES     | YES      | YES    | YES       | YES        | YES  |
| gross_profit      | YES  | maybe | maybe | YES     | YES      | YES    | YES       | YES        | YES  |
| sga               | YES  | YES   | YES   | YES     | YES      | YES    | YES       | YES        | YES  |
| rnd               | YES  | no    | no    | YES     | maybe    | maybe  | no        | YES        | YES  |
| depreciation      | YES  | YES   | YES   | YES     | YES      | YES    | YES       | YES        | YES  |
| ebit              | YES  | YES   | YES   | YES     | YES      | YES    | YES       | YES        | YES  |
| interest_expense  | YES  | YES   | YES   | YES     | YES      | YES    | YES       | YES        | YES  |
| taxes             | YES  | YES   | YES   | YES     | YES      | YES    | YES       | YES        | YES  |
| net_income        | YES  | YES   | YES   | YES     | YES      | YES    | YES       | YES        | YES  |
| eps_diluted       | YES  | YES   | YES   | YES     | YES      | YES    | YES       | YES        | YES  |
| shares_diluted    | YES  | YES   | YES   | YES     | YES      | YES    | YES       | YES        | YES  |
| cash              | YES  | YES   | YES   | YES     | YES      | YES    | YES       | YES        | YES  |
| receivables       | YES  | maybe | maybe | YES     | YES      | YES    | YES       | YES        | YES  |
| inventory         | maybe| no    | no    | YES     | YES      | maybe  | no        | maybe      | no   |
| total_assets      | YES  | YES   | YES   | YES     | YES      | YES    | YES       | YES        | YES  |
| total_liabilities | YES  | YES   | YES   | YES     | YES      | YES    | YES       | YES        | YES  |
| total_debt        | YES  | YES   | YES   | YES     | YES      | YES    | YES       | YES        | YES  |
| shareholder_equity| YES  | YES   | YES   | maybe*  | maybe*   | YES    | YES       | YES        | YES  |
| cfo               | YES  | YES   | YES   | YES     | YES      | YES    | YES       | YES        | YES  |
| capex             | YES  | YES   | YES   | YES     | YES      | YES    | YES       | YES        | YES  |
| buybacks          | maybe| maybe | no    | maybe   | maybe    | maybe  | no        | maybe      | maybe|
| dividends         | maybe| YES   | YES   | YES     | YES      | YES    | YES       | YES        | no   |
| acquisitions      | maybe| maybe | maybe | maybe   | maybe    | maybe  | maybe     | maybe      | maybe|

*shareholder_equity: LMT, MCD, SBUX may have negative equity (expected, not a bug)

Legend: YES = expect populated, no = expect NULL, maybe = depends on company

## Metric Ranges by Industry

| Metric        | Tech     | Banks   | REITs  | Defense  | Consumer | Energy  | Utilities | Healthcare | SaaS     |
|---------------|----------|---------|--------|----------|----------|---------|-----------|------------|----------|
| ROIC avg      | 15-40%   | skip    | 3-8%   | 15-30%   | 10-25%   | 8-20%  | 5-10%     | 10-30%     | 10-30%   |
| Rev CAGR 5y   | 10-25%   | 3-10%  | 3-8%   | 3-8%     | 3-10%    | -5-15% | 3-8%      | 5-15%      | 15-30%   |
| Gross margin  | 55-75%   | n/a    | n/a    | 20-35%   | 30-60%   | 20-40% | 30-50%    | 40-70%     | 65-80%   |
| D/E           | 0.3-1.5  | 5-15   | 2-8    | 1-5      | 0.5-3    | 0.3-1  | 1-3       | 0.3-1.5    | 0.5-2    |

These ranges are guidelines, not hard rules. Flag values outside 2x the range as anomalies.
