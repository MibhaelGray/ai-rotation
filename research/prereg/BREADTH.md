# Pre-registered: breadth from constituents (2026-10-25)

Committed with `research/breadth.py` before scoring. The signals passed the look-ahead check;
no returns were computed.

## Why

"A factor tops when fewer and fewer of its stocks carry it" is a classic market warning,
and it is the breadth idea from the start of this project. It could not be tested on ETFs
before, because there are no holdings in the data. With today's S&P 500 members, mapped to
GICS sectors and sub-industries, baskets can be built the way the page builds the AI layers,
and their breadth measured.

## Universes

| universe | baskets | from | minimum per week |
|---|---|---|---|
| S&P sub-industries vs SPY | 70 GICS sub-industries with 3+ members | 1999 | 10 |
| S&P sectors vs SPY | 11 GICS sectors | 1999 | 8 |
| AI layers vs QQQ | the page's 31 layers | 2016 | 10 |

Each basket is an equal-weight daily index of its members, rebalanced daily. A member counts
only from the date it joined the S&P 500.

## Signals (higher = expected to outperform)

| name | definition | hypothesis |
|---|---|---|
| participation | share of members above their own 50-day average | broad participation carries a move on |
| participation_change | 4-week change in that share | improving breadth leads |
| narrow_leadership | −(mean − median of members' 63-day log returns) | a move carried by a few names fades |
| net_new_highs | share of members at a 252-day high minus share at a 252-day low, 5-day average | breadth thrusts lead |

## Rules

- **Scoring.** Each is scored once on the research period (before 2023) with the frozen
  scorecard's cell scoring, and logged to `log.jsonl` as a normal trial, so the bar keeps
  rising (about 1.65 to 1.66).
- **Pass.** The standard verdict, with a positive direction expected.
- **Holdout.** A pass takes the one-shot holdout, as authorised.

## Known limits

- **Survivorship.** These are today's S&P 500 members; companies that left the index are
  missing. Counting each from its join date limits look-back bias, but the baskets still lean
  toward firms that survived, more so in early years. The members' later success does not
  enter any signal directly.
- **The sub-industries start thin:** about 43 in 2005, 70 by 2022.
