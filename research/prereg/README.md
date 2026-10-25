# Pre-registered: return signals within quadrants (2026-10-25)

Committed before any of these were run. Each file is scored **once** on the research period
with the unchanged returns scorecard (`python research/evaluate.py research/prereg/<file>`).
A failure is final: no edits, re-windowing or re-scoring.

## Question

The regime backtester found that forecasting the next quadrant doesn't predict returns.
Earlier return research found three effects across the whole universe: the lottery spike,
skewness, and a pullback within a trend. Do they work as top and bottom warnings **inside**
the quadrant where they should matter?

## Tests

| file | quadrant | signal (higher = expected to outperform) | expected |
|---|---|---|---|
| q1_lottery_in_leading.py | Leading | −(largest daily relative return, 21 days) | positive score |
| q2_skew_in_leading.py | Leading | −(skewness of daily relative returns, 126 days) | positive score |
| q3_pullback_in_left_side.py | Lagging or Improving | mean rank of the vol-adjusted 26w-skip-4w relative trend and the −4w relative return | positive score |

The quadrant is the page's weekly RRG against each universe's benchmark (EMA 3, 10-week
base, 1-bar momentum). Names outside the quadrant get no signal, so each week's IC is
computed only among names in that quadrant.

## Rules

- **Pass.** The standard scorecard rules: |score| at or above the bar for the log's trial
  count when scored, the same IC sign in every scored cell, and the right direction in ≥ 60%
  of years. A negative score that clears the bar is reported, but it is not a pass for the
  stated hypothesis.
- **Scoring.** The three run in the order listed. Each adds one trial to `log.jsonl`, so the
  bar rises from about 1.57 to 1.60.
- **Holdout.** A pass goes to the holdout only on the user's decision.
- **Descriptive comparison, not a test.** Each conditioned score is set beside the same
  signal's unconditioned score already in the log, to show whether the quadrant filter helps.

## Known limits, stated in advance

- **Sectors universe.** 11 sectors, of which only about 3 are in Leading at once, fall below
  that universe's 8-name minimum. The Q1 and Q2 sector cells will drop out, and the score
  averages the cells that remain.
- **Thinner weeks.** Conditioning thins each week's cross-section. Weeks below a universe's
  minimum count are skipped, so ETFs in Leading (about 13 of 43) lose some weeks.
- **Placebo threshold.** The threshold comes from full-panel random walks, not
  quadrant-filtered ones. That is approximate, because the IC is computed on fewer names.
