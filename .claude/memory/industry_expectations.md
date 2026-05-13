# Industry Expectations

What fields should/shouldn't be populated, and what metric ranges are normal,
per industry category. Claude commands read this to avoid false-positive anomalies.

## Field Expectations by Industry

| Field             | Tech | Banks | REITs | Defense | Consumer | Energy | Utilities | Healthcare | SaaS |
|-------------------|------|-------|-------|---------|----------|--------|-----------|------------|------|
| revenue           | YES  | YES   | YES   | YES     | YES      | YES    | YES       | YES        | YES  |
| cogs              | YES  | maybe | no*   | YES     | YES      | YES    | no*       | YES        | YES  |
| gross_profit      | YES  | maybe | no*   | YES     | YES      | YES    | no*       | YES        | YES  |
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
| buybacks          | maybe| maybe | no*   | maybe   | maybe    | maybe  | no*       | maybe      | maybe|
| dividends         | maybe| YES   | YES   | YES     | YES      | YES    | YES       | YES        | no   |
| acquisitions      | maybe| maybe | maybe | maybe   | maybe    | maybe  | no*       | maybe      | maybe|

*shareholder_equity: LMT, MCD, SBUX may have negative equity (expected, not a bug)
*cogs/gross_profit REITs: O and similar REITs have fundamentally different IS structure — no COGS concept
*cogs/gross_profit Utilities: NEE uses utility-specific cost taxonomy (fuel + purchased power), not standard COGS tags
*buybacks REITs: legally required to distribute 90%+ of income as dividends — structural prohibition on buybacks
*buybacks/acquisitions Utilities: capital deployment goes into regulated rate base, not traditional buybacks/M&A

Legend: YES = expect populated, no = expect NULL, maybe = depends on company

## Metric Ranges by Industry

| Metric        | Tech     | Banks   | REITs  | Defense  | Consumer | Energy  | Utilities | Healthcare | SaaS     |
|---------------|----------|---------|--------|----------|----------|---------|-----------|------------|----------|
| ROIC avg      | 15-40%   | skip    | 3-8%   | 15-30%   | 10-25%   | 8-20%  | 5-10%     | 10-30%     | 10-30%   |
| Rev CAGR 5y   | 10-25%   | 3-10%  | 3-8%   | 3-8%     | 3-10%    | -5-15% | 3-8%      | 5-15%      | 15-30%   |
| Gross margin  | 55-75%   | n/a    | n/a    | 20-35%   | 30-60%   | 20-40% | 30-50%    | 40-70%     | 65-80%   |
| D/E           | 0.3-1.5  | 5-15   | 2-8    | 1-5      | 0.5-3    | 0.3-1  | 1-3       | 0.3-1.5    | 0.5-2    |

These ranges are guidelines, not hard rules. Flag values outside 2x the range as anomalies.

## SIC Code Ranges (Phase 1B)

| Category              | SIC Range   | Examples           |
|-----------------------|-------------|--------------------|
| technology (software) | 7372-7374   | MSFT, CRM, NOW     |
| technology (hardware) | 3571-3672   | AAPL               |
| banking               | 6000-6199   | JPM, BAC           |
| reits                 | 6500-6599   | O, SPG             |
| utilities             | 4911-4991   | NEE, DUK           |
| energy                | 1311-1389   | XOM, CVX           |
| pharma                | 2830-2836   | JNJ                |
| defense               | 3760-3769   | LMT, RTX           |
| securities            | 6200-6399   |                    |
| manufacturing (broad) | 2000-3999   |                    |
| retail (broad)        | 5200-5999   | AMZN (5961)        |
| services (broad)      | 7000-8999   | UNH (8000s)        |

## Phase 1C Metric Ranges by Industry

| Metric              | Tech     | Banks  | REITs  | Defense | Consumer | Energy  | Utilities | Healthcare | SaaS    |
|---------------------|----------|--------|--------|---------|----------|---------|-----------|------------|---------|
| Operating margin    | 25-45%   | 30-45% | 25-40% | 10-15%  | 10-25%   | 10-20%  | 15-25%    | 15-30%     | 10-25%  |
| FCF margin          | 20-35%   | skip   | skip   | 5-12%   | 5-15%    | 5-15%   | skip      | 10-25%     | 15-30%  |
| Cash conversion     | 1.0-1.5  | skip   | skip   | 1.0-1.3 | 0.8-1.3  | 0.8-1.5 | skip      | 0.9-1.4    | 1.0-2.0 |
| ROE                 | 20-50%   | 10-18% | 5-15%  | 30-80%  | varies*  | 10-25%  | 8-14%     | 15-35%     | 10-30%  |

*Consumer ROE: companies with negative equity (SBUX, MCD) return None — this is correct.
FCF margin / cash conversion for banks, REITs, utilities: less meaningful due to business model.

## Structural NULLs by Company (Phase 1B, updated 2026-05-12)

These are correct NULLs — the concept does not exist in the business model.
Do not flag these as data gaps or XBRL failures.

| Ticker | Field(s) | Why NULL is correct |
|--------|----------|---------------------|
| MA | cogs, gross_profit | Payment network — no cost of goods. Mastercard operates a network, not a factory. No COGS line in their P&L. |
| MCD | cogs, gross_profit | Franchise model — revenue is franchise fees + rent. No COGS concept; costs are "franchised restaurant costs" under a different taxonomy. |
| NEE | cogs, gross_profit | Regulated utility — costs are fuel + purchased power under utility-specific XBRL tags, not standard COGS. Low analytical value to add. |
| NEE | buybacks, acquisitions | Capital deployment goes into regulated rate base (grid/generation assets), not traditional buybacks or M&A. |
| O | revenue, cogs, gross_profit, ebit, sga | REIT — income statement is fundamentally different. Revenue recognition changed post-2019. FFO/AFFO/NOI are the meaningful metrics, not revenue/COGS. |
| O | buybacks | REITs must distribute 90%+ of income as dividends by law — structural prohibition on buybacks. |

Note: For O (Realty Income), the agent_bundle industry_notes already warns the qualitative agent
about REIT income structure. These NULLs are expected and should not trigger anomaly alerts.
