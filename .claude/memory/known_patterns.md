# Known Data Patterns

Patterns discovered during stress testing and spike work. These are NOT bugs —
they are expected behaviors that should not be flagged as anomalies.

## Negative Equity Companies

- **SBUX, MCD, LMT**: Have negative shareholder equity due to aggressive buyback programs.
  - ROIC returns None (invested capital <= 0) — this is correct, not a bug.
  - D/E returns None (equity <= 0) — this is correct.
  - Valuation via sticker price still works (uses EPS, not equity-based).
  - Fixed in Phase 1A (BUG-3): `roic_series()` checks `inv_cap > 0`, `latest_debt_to_equity()` checks `equity <= 0`.

## Banks (JPM, BAC)

- ROIC is meaningless for banks — deposits are not traditional debt, interest is revenue.
- `inventory` will always be NULL — banks don't hold inventory.
- `cogs` may be NULL or misleading — banks don't have traditional cost of goods.
- `receivables` may map to loan portfolios, not traditional AR.
- Interest coverage is inverted — interest is a core business metric, not overhead.

## REITs (O, SPG)

- EPS is misleading — FFO (Funds From Operations) is the real metric, which we don't capture yet.
- High leverage is structural and expected, not a moat failure.
- `depreciation` is large relative to earnings (real estate heavy).
- `inventory` will be NULL.

## Utilities (NEE, DUK)

- Low ROIC (5-10%) is structural due to regulation, not a moat failure.
- Growth rates are typically low (2-5%) — this is normal.
- High debt levels are structural (capital-intensive regulated business).

## Energy (XOM, CVX)

- Revenue is highly cyclical — single-year growth metrics can be misleading.
- Uses `Revenues` tag, not `RevenueFromContractWithCustomer...` — fixed in Phase 1A enrichment.

## SaaS (CRM, NOW)

- High SBC (stock-based compensation) distorts EPS.
- `rnd` should be high relative to revenue (30-50%).
- `inventory` will be NULL — no physical goods.

## Zero Growth

- A company with g=0.0 is valid. Previously BUG-1 treated 0.0 as falsy in the or-chain.
  Fixed in Phase 1A: uses `is not None` checks instead of truthiness.

## SIC Code Mapping (Phase 1B)

- SIC codes come from the SEC submissions endpoint (`/submissions/CIK{cik}.json`).
- `sic_to_category()` checks specific ranges first (banking 6000-6199, tech 7372-7374, etc.) before broad SIC division ranges (manufacturing 2000-3999, services 7000-8999).
- If the submissions endpoint fails, ingestion still succeeds — SIC fields are NULL but financial data is unaffected.
- `industry_notes` are plain-English guidance strings for the agent, NOT suppression logic.

## Negative Equity and ROE (Phase 1C)

- `roe_series()` uses the same guard as `roic_series()`: returns None when equity <= 0.
- This is correct for SBUX, MCD, LMT — negative equity from buybacks makes ROE meaningless.

## Cash Conversion Caveats

- `cash_conversion_series()` = CFO / Net Income. Values > 1.0 are good (high-quality earnings).
- For banks and REITs, cash conversion is less meaningful — their CFO includes different items.
- A negative ratio (positive CFO, negative NI) is valid and informative but shouldn't be scored.
