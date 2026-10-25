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

## Results (scored once, 2026-10-25)

| test | score | bar | verdict | why |
|---|---|---|---|---|
| Q1 lottery within Leading | +0.73 | 1.57 | fail | below the bar; right direction in 58% of years |
| Q2 skewness within Leading | +0.21 | 1.58 | fail | below the bar; IC turns negative on AI stocks |
| Q3 pullback-in-trend within Lagging/Improving | +0.29 | 1.58 | fail | below the bar; IC negative on ETFs |

As stated in advance, the sector cells dropped out of Q1 and Q2.

**Descriptive comparison: mean rank IC with the quadrant filter vs without it**

| signal | ETFs 4w | ETFs 13w | AI stocks 4w | AI stocks 13w |
|---|---|---|---|---|
| lottery, all names | +0.038 | +0.042 | +0.038 | +0.041 |
| lottery, Leading only | +0.039 | +0.081 | +0.019 | +0.029 |
| skewness, all names | +0.067 | +0.088 | −0.000 | −0.010 |
| skewness, Leading only | +0.030 | +0.071 | −0.002 | −0.018 |
| pullback-in-trend, all names | +0.025 | +0.027 | +0.044 | +0.021 |
| pullback-in-trend, left side only | −0.007 | −0.006 | +0.032 | +0.019 |

**Reading.** The quadrant filter does not sharpen these effects. They are as strong or
stronger across the whole universe. The pullback effect disappears entirely left of centre,
so it belongs to names that are already strong. The one cell where the filter helped
(lottery among Leading ETFs at 13 weeks, IC doubled) is a single cell out of twelve: worth
noting, not acting on, and a formal test of it would be a new trial.

---

# Pre-registered: ATR and volume batch (2026-10-25)

Committed before scoring. The files passed the scorecard's shape and look-ahead checks;
no forward returns were computed. Each is scored once with
`python research/evaluate.py research/prereg/<file>`, in the order below, and adds one trial
to `log.jsonl`: the bar rises from about 1.58 to 1.60.

## Why these

None of these has been scored on returns before. ATR appeared only in the regime test,
which asks a different question. The volume ideas already in the log combined volume with
other legs (a volume-weighted pullback, capitulation day counts); these test volume and ATR
on their own.

## Tests

| file | signal (higher = expected to outperform) | rationale |
|---|---|---|
| v1_atr_overextension.py | −(close − 50-day SMA) / 14-day ATR | moves stretched in their own volatility units mean-revert |
| v2_abnormal_volume.py | log(20-day average volume / 250-day average) | the high-volume return premium |
| v3_accumulation.py | log(volume on relative up days / volume on relative down days), 50 days | accumulation precedes outperformance |
| v4_capitulation_atr.py | −(20-day relative log return) × (10-day ATR / 60-day ATR) | a volatile selloff marks seller exhaustion |

## Rules

- **Pass.** The standard scorecard rules at the bar in force when each is scored.
- **Direction.** Each is expected to score positive. A negative score past the bar is
  reported as a finding about the opposite effect, but it is not a pass.
- **One shot.** A fail is final, and none is retuned. A pass goes to the holdout only on the
  user's decision.

## Known limits

- **Volume units.** Volume is in shares of each listing, so V2 and V3 compare a name only
  with its own history. That makes them unit-free.
- **ETF volume** reflects creation and redemption activity as well as investor demand.

## Results (scored once, 2026-10-25): all four fail

| test | score | bar | ETFs 4w / 13w | Sectors 4w / 13w | AI stocks 4w / 13w |
|---|---|---|---|---|---|
| V1 ATR overextension | +0.05 | 1.59 | −0.22 / −0.32 | +0.62 / +0.35 | +0.60 / −0.70 |
| V2 abnormal volume | −0.39 | 1.59 | −0.59 / −0.54 | −1.03 / −0.89 | +0.44 / +0.28 |
| V3 accumulation | +0.32 | 1.60 | +0.38 / +0.28 | +0.25 / +0.10 | −0.23 / +1.13 |
| V4 capitulation (ATR) | +0.38 | 1.60 | +0.03 / +0.03 | +0.63 / +0.58 | +1.18 / −0.16 |

(The cells are ratios: IC t divided by the placebo t95.)

**Reading.**
- **No consistent effect.** None of the four has the same sign in every cell, and every
  score is far from the bar.
- **ATR overextension** says nothing about future returns.
- **Abnormal volume** points opposite ways by universe: heavy volume comes before
  *under*performance in ETFs and sectors (−0.4 to −1.0) and slightly before outperformance in
  AI stocks. That fits ETF volume tracking flows that arrive late, but the effect is too weak
  to call.
- **Accumulation** clears noise in one cell only (AI stocks at 13 weeks, +1.13).
- **Capitulation scaled by ATR** clears noise in one cell only (AI stocks at 4 weeks, +1.18).
  It is near zero on ETFs.

Single-cell hits like the last two are what 24 cells of noise produce now and then. They do
not justify a retuned retry.
