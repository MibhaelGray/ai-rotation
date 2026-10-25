# Pre-registered: overnight combination search (2026-10-25)

Committed with `research/search.py` before discovery ran. The features, the combination rule,
the split, the shortlist size and the pass rules are all fixed here.

## The problem this design solves

Searching thousands of combinations always finds some that look great on the data used to
pick them. Raising the scorecard's bar for every one of 13,000 trials would make a pass
nearly impossible. Picking the best and scoring it on the same data would make one
meaningless. So the research period (before 2023) is split:

| stage | signal dates | universes | what happens |
|---|---|---|---|
| Discovery | 1999-2010, with outcomes also before 2011 | ETFs, sectors | every combination is screened; the best 20 distinct ones are shortlisted |
| Validation | 2011-2022 | ETFs, sectors, AI stocks | the 20 are scored once each, on years and AI stocks that discovery never saw |
| Holdout | 2023 onward | all | any validated finalist takes evaluate.py's one-shot exam |

## Candidates

- **Features.** 30, all causal, all passing the scorecard's look-ahead check: lottery, crash
  (largest daily drop), skewness, volatility, the volatility ratio, continuity, efficiency,
  beta, RSI of RS, 26w-skip-4 momentum, 12-week momentum, 52w-skip-4 momentum, the 4-week and
  1-week reversals, the 52-week RS high, the 40-week trend, RS-Ratio, RS-Momentum, RRG
  distance, the RS-Ratio z-score, quadrant tenure, the 200-day trend, ATR stretch, range
  expansion, close location, squeeze, abnormal volume, accumulation, capitulation, and Amihud
  illiquidity. Definitions are in `FEATURES` in search.py.
- **Combinations.** Every set of 1, 2 or 3 features (4,525 sets), each the equal-weight mean
  of the features' cross-sectional percentile ranks. Each feature's direction is fixed once,
  by the sign of its own mean discovery IC.
- **Subsets.** Each set is scored on all names, on names right of centre on the weekly RRG
  (RS-Ratio ≥ 100), and on names left of it. That makes 13,575 candidates, and the subsets
  are how regime position enters the search.

## Discovery ranking and the shortlist

- **Ranking.** The discovery score is the mean Newey-West t of the weekly rank IC over the
  cells with enough weeks. A candidate needs all 4 cells (ETFs and sectors × 4 and 13 weeks)
  with every cell's t above 0.
- **Shortlist.** The 20 best by discovery score, skipping any whose discovery IC series
  correlates above 0.9 with one already picked, so the shortlist is not 20 copies of one idea.
- **Expect left- and right-side candidates to drop out.** Sector cells fall below the 8-name
  minimum when only one side of the chart is used, which leaves them under 4 cells.

## Validation (one shot)

- **Scoring.** Each shortlisted candidate is scored once on 2011-2022 with the frozen
  scorecard's own cell scoring: rank IC t divided by a random-walk placebo t95 for that
  window, averaged over the 6 cells.
- **Pass.** The scorecard verdict with the bar Bonferroni-adjusted for 20 candidates (about
  1.54), the same IC sign in every cell, the right direction in at least 60% of years, and
  the same direction as discovery.
- **No retries.** No re-runs, re-ranking or swapping of shortlist members after validation.

## Holdout

The user has authorised running it without asking. Each validated finalist is written out as
its exact signal file, scored on the research period with `evaluate.py` (logged as a normal
trial), and then given `evaluate.py --holdout --confirm` once. A finalist that fails there is
finished.

## Known limits

- **Discovery leans on ETFs.** The ETF and sector universes overlap (sectors are inside the
  ETF list), so discovery is mostly one ETF cross-section. AI stocks enter only at validation.
- **The split is in time.** Effects that changed after 2010 will fail validation, which is the
  point.
- **The earlier work saw all of 1999-2022.** The 30 features include effects found in the
  earlier research, which used the whole research period, so validation is not fully blind to
  them. The holdout is the fully clean test.
