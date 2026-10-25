# Pre-registered: round 2, market-regime conditioning (2026-10-25)

Committed with `research/search_regime.py` before its discovery ran. It was written after
round 1's validation results were known; that is stated here, and the bar below accounts for
it.

## Question

Do any of the same 4,525 feature sets work only in one market regime? Bull weeks are when
the universe's benchmark (SPY, or QQQ for AI stocks) closes above its 40-week average;
bear weeks are below it. A candidate is scored only on that regime's weeks.

## Unchanged from round 1

- **Features and combinations.** The same 30 features. Each set of 1-3 is combined by
  equal-weight percentile rank.
- **Directions.** Fixed by round 1's discovery signs, copied from `shortlist.json` and not
  re-estimated.
- **Split.** Discovery on 1999-2010, with outcomes before 2011, on ETFs and sectors.
  Validation once on 2011-2022 on all three universes.
- **Ranking and shortlist.** Mean discovery t; all 4 cells positive; the 20 best with a 0.9
  overlap filter.

## Different

- **Subsets.** Bull and bear instead of all/right/left, which gives 9,050 candidates.
- **Bar.** Validation reuses 2011-2022, which round 1 already scored 20 candidates on. The
  bar is Bonferroni-adjusted for all 40: z(1 − 0.05/80)/1.96, about 1.65.

## Rules

- **Validation pass.** The scorecard verdict at that bar, the same direction as discovery,
  and one shot only.
- **Holdout.** A validated finalist goes to the holdout, as authorised.

## Known limits

- **Bear weeks are a minority** (roughly a third), so bear candidates rest on fewer weeks and
  their Newey-West t treats the gaps between regime spells as adjacent.
- **The regime is defined by each universe's own benchmark,** so for AI stocks it is QQQ's
  trend.

## Result (2026-10-25): 0 of 20 pass validation (bar 1.65)

- **Discovery.** 9,050 candidates in 14 seconds. The shortlist splits into bull-market
  candidates (negative skewness plus squeeze, trend or low-ATR-stretch legs) and bear-market
  candidates (illiquidity, i.e. Amihud, plus low volatility, short-term reversal or weak
  closes).
- **Validation (2011-2022).** Scores run from +0.13 to +0.78. The two kinds split by universe:
  - **Bull candidates** hold on ETFs and sectors, with ratios of 1.0-1.6 at 4 weeks, but
    turn negative on AI stocks at 13 weeks.
  - **Bear candidates built on illiquidity** are the strongest single cells of the night on
    AI stocks at 13 weeks: +2.84 for skew + 1-week reversal + Amihud, +2.49 and +2.05 for the
    others. They are near zero on ETFs and sectors.
- **Reading.**
  - **Negative skewness** works on ETFs in rising markets.
  - **Illiquid AI stocks rebound after bear-market selloffs,** which is the classic
    liquidity premium. But the 2011-2022 bear weeks for QQQ are a few spells, mostly
    2018-19 and 2022, so that is a handful of episodes, not hundreds.
  - Neither effect holds across universes, which the pass rule requires, and nothing reaches
    the holdout.
