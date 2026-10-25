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
