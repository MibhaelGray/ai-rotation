# Pre-registered: confirm the near-miss on universes it has never seen (2026-10-25)

Committed before running. `python research/confirm.py` runs it once and refuses a second run.

## Why

The best returns candidate, "skewness + lottery + pullback-in-trend, equal thirds" (hash
`e55c5c5fc3c9`), scored +1.55 against a bar of 1.56 on the original universes. Another
attempt on those same universes would only raise the bar. A test on funds it has never been
scored on is independent evidence: if the effect is real it should show up there too.

## Signal

`research/prereg/confirm_combo.py` is a byte-for-byte copy of the logged source, and the
runner checks its hash. It has no new parameters, windows or weights.

## Universes (fixed now; none added or dropped later)

| universe | benchmark | funds | minimum funds per week |
|---|---|---|---|
| Country ETFs vs EFA | EFA | 32 iShares single-country funds (EWA, EWC, EWJ, EWZ, FXI, INDA ...) | 10 |
| US style ETFs vs SPY | SPY | 29 size, value/growth, quality, momentum, low-vol and dividend funds | 10 |

The exact lists are in `research/confirm.py`. A fund enters when its history starts.
Horizons are 4 and 13 weeks, which gives 4 cells.

- **Countries** are the genuinely independent test: different markets, currencies and
  holdings from anything scored before.
- **Styles** are US equities that overlap the original sector ETFs in holdings, but they are
  a different cross-section. It is the weaker of the two tests.

## Rules

- **Period.** Research only, before 2023-01-01. The holdout stays sealed.
- **Scoring.** The frozen scorecard's own cell scoring and verdict: each cell's IC t is
  divided by its own random-walk placebo t95, and the score is the mean of the four ratios.
- **Pass.** All of these:
  1. score ≥ +1.00, the scorecard's bar for a single trial, since this is one
     pre-registered hypothesis;
  2. a positive IC in all 4 cells;
  3. the right direction in at least 60% of calendar years.
- **One shot.** Run once. A fail is final for this signal: no edits, and no swapping of
  universes or benchmarks.
- **If it passes.** That earns the one-shot 2023+ holdout
  (`evaluate.py --holdout --confirm research/signal.py`), but only on the user's decision.

## Known limits, stated in advance

- **Survivorship.** These are funds that still exist today; closed country or style funds
  are missing.
- **Shorter histories.** Several funds start between 2007 and 2013 (EIS, TUR, THD, ECH,
  EPOL, EIDO, EPHE, ENZL, INDA, MCHI, SPLV, USMV, MTUM, QUAL, VLUE, SPHB, SCHD). Early years
  have fewer names, and weeks under the minimum are skipped.
- **Correlated styles.** Style funds move together closely (IWB is almost SPY), so the
  style cross-section is narrow and noisy.
