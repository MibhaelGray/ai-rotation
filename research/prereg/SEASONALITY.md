# Pre-registered: return seasonality (2026-10-25)

Committed before scoring. Both files passed the look-ahead check. Each uses a forward return
only from at least a year ago, so `shift(-H)` inside them never reaches past the current row.
No returns were scored before the commit.

## Why

Published work finds that industries and countries tend to beat the market in the same
calendar months year after year: return seasonality (Heston & Sadka; Keloharju, Linnainmaa &
Nyberg). Nothing tested so far used the calendar.

## Signals (higher = expected to outperform)

| file | signal |
|---|---|
| s_seasonality_4w.py | mean relative log return over the 4 weeks starting on this calendar date, in each of the past 1-20 years (at least 5) |
| s_seasonality_13w.py | the same over 13 weeks |

## Rules

- **Scoring.** Each is scored once with `evaluate.py` and logged as a normal trial; the bar
  rises from about 1.63 to about 1.64.
- **Pass.** The standard verdict, with a positive direction expected. A pass takes the
  one-shot holdout, as authorised.

## Known limits

- **AI stocks have only about 14 months of seasonality** (Oct 2021 - Dec 2022), because the
  10-year fetch starts in 2016 and the signal needs 5 prior years. That cell may drop out,
  and if it stays it is thin.
- **ETFs start in 2004** for the same reason.
