# Pre-registered: round 5, timing search (2026-10-25)

Committed with `research/search_ts.py` before its discovery ran. Rounds 1-4 had already been
scored and seen when this was written.

## Question

Can an indicator tell **when** a given factor will beat its benchmark, judged against that
factor's own history? Every earlier test ranked factors against each other each week. This
is the timing question behind "is this factor about to rotate".

## Method

- **Features.** The same 30 features as search.py.
- **Standardising.** Each feature is z-scored per factor against its own expanding history,
  using at least 104 weeks, past and current rows only, and clipped at ±3.
- **Position.** The mean z of 1-3 features (4,525 sets), clipped at ±2. A positive position
  is long the factor against the benchmark; a negative one is short.
- **Directions.** Each feature's direction is the sign of its own mean discovery t.
- **Cell statistic.** The weekly mean over factors of position × the forward relative log
  return over H weeks (4 or 13), with a Newey-West t (H lags). Weeks with fewer factors than
  the universe's minimum are skipped.
- **Split.**
  - Discovery: 1999-2010, with outcomes before 2011, on ETFs and sectors.
  - Shortlist: the 20 best by mean discovery t, with all 4 cells positive, skipping any whose
    discovery return series correlates above 0.9 with one already picked.
  - Validation: once, on 2011-2022, on all three universes.

## Validation rules

- **Ratio.** Each cell's t is divided by the 95th percentile |t| of 200 random-walk positions
  built the same way (z-scored and clipped) on that cell.
- **Pass.** All of these:
  1. the mean ratio is at or above the bar, Bonferroni-adjusted for every candidate validated
     on 2011-2022: rounds 1-2's 40 plus these 20, so K = 60 and the bar is about 1.70;
  2. every cell is positive;
  3. the mean share of positive years is at least 60%.
- **Holdout.** A pass takes the holdout, as authorised. That needs a holdout runner for this
  statistic, written then, with no changes to the signal.

## Known limits

- **Costs.** Returns are gross. Timing positions change slowly, but costs are not deducted.
- **The z-score needs two years of history,** so AI stocks enter in late 2018.
- **Factors move together.** The weekly mean pools factors whose relative returns are
  correlated, and the placebo handles that the same way.

## Result (2026-10-25): 0 of 20 pass validation (bar 1.70)

- **Discovery.** 4,525 candidates in 23 seconds. The shortlist is almost entirely
  top-warnings: short the factor against its benchmark when, against its own history, it
  shows lottery-like spikes, right-skewed returns and an extended trend (12-month momentum,
  40-week trend, RS-Ratio, RSI). Discovery t-stats were 3.6-4.2.
- **Validation (2011-2022).** Scores run from −0.28 to +0.36. Sectors at 13 weeks are
  negative for 19 of the 20.
- **Reading.** Timing a factor against its own history fails out of sample more completely
  than any cross-sectional test did. The top-warning pattern was a 1999-2010 artefact, or at
  least it did not survive into 2011-2022. Nothing reaches the holdout.
