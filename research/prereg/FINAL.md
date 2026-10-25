# Pre-registered: the final exam (2026-10-25)

Committed before running. `python research/final.py` runs once and refuses a second run.

## The signal

The equal-weight mean of two cross-sectional percentile ranks, on all names (no RRG subset),
built exactly as `search.make_signal` does:

1. **negative skewness** of daily relative returns over 126 days, and
2. **negative 1-week relative return** (last week's laggards).

## Why this one

It is the simplest form of what every round on pre-2023 data converged on:

- **Round 1 (ETFs).** All 20 shortlisted were built on negative skewness, and most had the
  1-week reversal as well.
- **Round 9 (baskets).** The same core, positive in all six validation cells for the best
  versions, AI layers included.
- **Skewness alone.** Passed on the country and style ETFs.

It is defined now, from that pre-2023 evidence alone. Nothing about it was chosen by looking
at 2023+.

## What has and hasn't seen 2023+

- **Seen once, and only for skewness alone:** the holdout of the ETF, sector and AI-stock
  universes. This combination shares that leg, so those three universes are not fully blind.
- **Never scored by anything:** the 2023+ data of the country ETFs, style ETFs, S&P
  sub-industry baskets, S&P sector baskets and AI layers. The one exception is the descriptive
  bear-week check on AI and S&P stocks, a different signal and different universes.

## Universes (8, so 16 cells)

ETFs vs SPY, Sectors vs SPY, AI stocks vs QQQ, Country ETFs vs EFA, US style ETFs vs SPY,
S&P sub-industries vs SPY, S&P sectors vs SPY, and AI layers vs QQQ, each scored on 4 and 13
weeks.

## Pass rule (the scorecard's single-test verdict)

1. The mean of the 16 cell ratios (IC t ÷ placebo t95 on 2023+) is at least 1.00.
2. The IC has the same sign in every cell.
3. The direction is right in at least 60% of years.

The holdout covers under four years (2023 to 2026-10), so every cell has low power. The
same-sign rule across 16 cells is strict, and that is accepted in advance.

## After

- **Pass or fail, this ends the night's search.** A pass is the first signal in this project
  to clear data it was never fitted to. A fail means nothing here is strong enough to trade
  on price data alone.
- **No version of it will be tweaked and re-run.**

## Result (run once, 2026-10-25): fail

Score +0.28 against a bar of 1.00, and the IC sign differs across cells.

| universe | 4w ratio | 13w ratio | 13w net per period |
|---|---|---|---|
| ETFs vs SPY | +0.65 | +0.77 | +0.95% |
| Sectors vs SPY | +0.37 | +0.53 | +1.06% |
| AI stocks vs QQQ | +0.20 | −0.10 | −1.31% |
| Country ETFs vs EFA | +0.31 | −0.05 | −0.91% |
| US style ETFs vs SPY | +0.42 | +0.34 | +0.29% |
| S&P sub-industries vs SPY | +0.36 | +0.19 | −0.02% |
| S&P sectors vs SPY | +0.30 | +0.38 | +0.79% |
| AI layers vs QQQ | −0.22 | +0.05 | −0.79% |

**Reading.**
- **The sign mostly held:** 13 of 16 cells are positive. On the ETF and sector universes,
  the direction and rough size of the pre-2023 effect continued into 2023-2026.
- **No cell clears its noise threshold** over the short holdout.
- **The AI stocks and AI layers show nothing,** which is the universe this project cares
  about most.
- **At 4 weeks the 1-week reversal leg trades too often** and loses to costs.

This ends the price-data search, as stated above.
