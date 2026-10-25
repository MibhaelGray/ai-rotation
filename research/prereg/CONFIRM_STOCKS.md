# Pre-registered: the bear-market illiquidity effect on S&P 500 stocks (2026-10-25)

Committed before running. `python research/confirm_stocks.py` runs each test once.

## Why

Round 2's strongest validation cells were on AI stocks at 13 weeks, from bear-market
candidates built on Amihud illiquidity: +2.84 for skewness + 1-week reversal + illiquidity.
The same candidates did nothing on ETFs. If this is a real stock-level effect (illiquid
stocks rebound after bear-market selloffs, the liquidity premium), it should show up on
other stocks.

## Universe

The ~500 current S&P 500 stocks against SPY, research period only (1999-2022). Each stock
counts from the date it joined the index, and each week needs at least 50 stocks. Neither
candidate was ever scored on these stocks.

## Tests (higher = expected to outperform)

Both are scored only in weeks when SPY closes below its 40-week average, exactly as
`search_regime.make_signal` builds them.

| test | signal |
|---|---|
| bear: skew + 1w reversal + illiquidity | round 2's candidate, unchanged |
| bear: illiquidity alone | the Amihud leg alone, to see whether illiquidity is doing the work |

## Rules

- **Pass.** The bar is for 2 tests, z(1 − 0.05/4)/1.96 ≈ 1.14, across the 2 cells (4 and 13
  weeks), with the same positive IC sign in both and the right direction in at least 60% of
  years.
- **Holdout.** A pass would take the 2023+ holdout as authorised. But the candidate is
  defined only in bear weeks, and the holdout has few (QQQ and SPY were below their 40-week
  averages mostly in 2022, which is before the holdout, and briefly in 2025). If the holdout
  has too few bear weeks to score, that will be reported rather than forced.

## Known limits

- **Survivorship.** Today's members only. That flatters illiquid stocks in particular,
  because the illiquid stocks that failed are missing. This test therefore leans toward
  passing, so a fail is the more informative outcome.
- **Shares are mostly US large caps,** which are more liquid than many of the foreign AI
  listings, so the illiquidity spread is narrower.

## Result (run once, 2026-10-25): both PASS on the research period

| test | 4w ratio (IC) | 13w ratio (IC) | score | net per H (4w / 13w) | years right |
|---|---|---|---|---|---|
| bear: skew + 1w reversal + illiquidity | +2.33 (+0.061) | +2.49 (+0.097) | **+2.41** | +1.08% / +3.50% | 81% / 86% |
| bear: illiquidity alone | +1.44 (+0.046) | +1.53 (+0.089) | **+1.49** | +0.98% / +3.36% | 76% / 86% |

Both clear the 2-test bar of 1.14. The survivorship caveat above applies with full force:
the failed illiquid stocks of 2000-02 and 2008-09 are missing, which flatters exactly this
signal.

## The holdout can't be scored formally (decided before looking at any 2023+ outcome)

Since 2023-01-01, SPY has closed below its 40-week average in only 16 weeks:
2023-01, 2023-03, 2023-10, 2025-03 to 05 and 2026-03 to 04. QQQ has 17. The scorecard needs at
least 16 weeks of IC for a 4-week cell and 34 for a 13-week cell, so a formal holdout would
be empty or nearly so. As stated above, that is reported rather than forced.

**Descriptive check, committed before running, not a test.** For the combined candidate,
report the mean weekly rank IC and the share of positive weeks over the 2023+ bear weeks at 4
and 13 weeks, on S&P 500 stocks and on AI stocks. The pass/fail verdict stays the research
result above, with its caveat. This only says whether the recent bear episodes point the
same way.
