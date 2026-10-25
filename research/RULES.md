# Signal research rules

The aim is a signal that warns of relative tops and bottoms 1-3 months ahead and survives data
it has never seen. Most ideas will fail; the rules exist so that the ones that pass can be believed.

## What may change

- **Only `research/signal.py`.** It defines `signal(px, bench, bars)`, plus `NAME` and a one-line `IDEA`.
- **Never** `research/evaluate.py`, `scripts/backtest.py`, the cached data, the universes,
  horizons, costs or `HOLDOUT_START`. A change to any of them resets the experiment: delete
  `log.jsonl` and start the count again, and say so in the commit.

## The signal contract

- Input: weekly Friday closes for one universe and its benchmark, plus `bars`: high, low and
  volume, weekly (`bars.high`, `.low`, `.volume`, `.close`) and daily (`bars.daily.*`), for the
  same tickers and the benchmark. That covers ATR, range expansion, gaps, closes off the
  lows and volume spikes. Volume is in shares of the listing (local for foreign names), so
  compare it only with that name's own history.
- Output: weekly, shaped like `px`. Higher = expected to outperform over the next 1-3 months.
- Only past and current rows. The scorecard re-runs every signal on truncated data and rejects
  any whose past values change (no `shift(-k)`, whole-sample means or ranks, centred windows).

## The scorecard

`python research/evaluate.py` scores the signal on the research period (before 2023-01-01) in
six cells: three universes (sector and industry ETFs vs SPY from 2000, the 11 sectors vs SPY
from 1999, the AI stocks vs QQQ from 2016) by two horizons (4 and 13 weeks).

- **Cell ratio:** rank-IC t-stat ÷ the 95th-percentile t of 200 random-walk signals on the same panel.
- **Score:** the mean of the six ratios.
- **PASS** needs all three:
  1. |score| at or above the bar, which rises with every distinct signal ever logged
     (Bonferroni-adjusted: 1.00 for the first, about 1.4 after 10, 1.7 after 50, 1.8 after 100);
  2. the same IC sign in every cell;
  3. the right direction in at least 60% of calendar years.

Every run is appended to `log.jsonl` with its source code and a hash. The log is the trial count
and is never edited. Commit it.

## The holdout (final exam)

`python research/evaluate.py --holdout --confirm <file>` scores 2023 onward, **once** per signal,
and only for a file already scored on the research period. Use it only on finalists that
PASS, a handful at most over the whole project. A signal that fails there is finished: do not
tweak it and resubmit. Results go to `holdout_log.jsonl`.

## The agent loop

`python research/agent.py --rounds N` (needs `ANTHROPIC_API_KEY`) runs N rounds. In each,
Claude Opus 5.5 reads these rules, the baselines and every logged result, and writes one
candidate. The harness checks the code (numpy, pandas, math and statistics only, no file or
interpreter access), saves it under `candidates/`, copies it to `signal.py` and scores it.
`agent_log.jsonl` keeps each round's hypothesis, outcome and token use. The loop stops at the
first PASS and never runs the holdout. `--dry-run` scores the current `signal.py` once with
`--scratch` (not logged, no API call) to check the plumbing.

A round costs one Opus call, roughly 10-30k tokens in and a few thousand out. That is about
$0.10-0.20 at list prices, more as the log grows.

## Baselines

`baseline.md` holds the page's existing signals (scored with `--baselines`). The best, 26-week
momentum skipping the latest month and its volatility-adjusted version, score about +0.54
against a bar of about 1.4. None passes. A new idea has to clearly beat them, not just match them.

## Known limits

- The AI universe was chosen in hindsight and has only 6 research years; the ETF universes
  carry most of the evidence.
- Prices, highs, lows and volume only. Positioning, flows, short interest and options history
  are not in the data. Adding a source changes the scorecard and resets the log.
- Foreign names' highs and lows come from their local high/close and low/close ratios applied
  to the USD close, so they are exact up to the day's currency move.
- The log was reset on 2026-10-21 when highs, lows and volume were added. It starts with
  the 9 baselines.
