# Pre-registered: the leads on small and mid caps (2026-10-25)

Committed with `research/smallcap.py` before running. The signals passed the look-ahead
check on these universes; no returns were computed. `python research/smallcap.py` runs once.

## Why

These are about 1,000 stocks that nothing in this project has ever been scored on, in any
period. That makes them the cleanest check left of tonight's leads, which were all chosen on
other data.

## Universes

| universe | names | benchmark |
|---|---|---|
| S&P 400 stocks | the ~400 current members | MDY |
| S&P 600 stocks | the ~600 current members | IJR |
| S&P 400 sub-industry baskets | GICS sub-industries with 3+ members, equal weight | MDY |
| S&P 600 sub-industry baskets | the same | IJR |

Stocks added inside Wikipedia's change log (S&P 400 from 2012, S&P 600 from 2019) count only
from their add date. Members added earlier have no date and count from their first price.

## Tests (signals built exactly as in search.py / search_regime.py)

| test | universes | where it was chosen |
|---|---|---|
| low skew | all four | skewness, passed on country/style ETFs (CONFIRM_SKEW.md) |
| low skew + 1w losers | all four | the final exam signal (FINAL.md) |
| bear rebound: skew + 1w reversal + illiquidity, only weeks the benchmark is below its 40-week average | the two stock universes | round 2, AI stocks (CONFIRM_STOCKS.md) |
| skew + 1w losers + falling RS-Momentum | the two basket universes | round 9's best (SEARCH_BASKETS.md) |

## Rules

- **Research period (before 2023): the primary test.** Scorecard verdict with the bar for 4
  tests, z(1 − 0.05/8)/1.96 ≈ 1.28: the same IC sign in every cell, the right direction in at
  least 60% of years, and a positive direction.
- **2023+: reported in the same run, as a confirmation.** Single-test bar of 1.00. Bear-week
  cells will likely fall below the scorecard's minimum weeks and drop out; that is accepted.
- **Confirmed** means a pass on the research period and a pass, or at least the same sign in
  every remaining cell, on 2023+.
- **One shot.** No tweaks.

## Known limits

- **Survivorship is heavy here.** These are today's members, most without join dates, and
  small caps that failed or were dropped are missing. That flatters anything favouring
  beaten-down or illiquid names, the bear rebound in particular, so a pass needs the 2023+
  check to mean much.
- **Wikipedia's GICS labels are today's,** applied to the whole history.

## Result (run once, 2026-10-25)

| test | research score (bar 1.27) | 2023+ score (bar 1.00) | verdict |
|---|---|---|---|
| low skew | +0.29 | +0.78, positive in all 8 cells | fail |
| low skew + 1w losers | +1.20, mixed signs | +0.77, positive in all 8 cells | fail (near miss) |
| **bear rebound: skew + 1w reversal + illiquidity** | **+3.32** (cells +3.0 to +3.7) | **+1.37** (3 cells; S&P 400 13w had too few weeks) | **PASS on both** |
| skew + 1w losers + falling RS-Momentum | +0.77 | +0.41 | fail |

**The bear rebound on 2023+:**

| universe | H | IC | ratio | net spread per period | years right |
|---|---|---|---|---|---|
| S&P 400 stocks | 4w | +0.064 | +1.80 | +1.28% | 100% |
| S&P 600 stocks | 4w | +0.033 | +0.61 | +0.85% | 100% |
| S&P 600 stocks | 13w | +0.063 | +1.68 | +3.58% | 100% |

**Caveat before believing it.** Survivorship flatters this signal most of all: small caps that
were removed from the index after collapsing are missing, and they are exactly the
illiquid losers that did not rebound. That applies to 2023+ too. See the survivorship check
below.
