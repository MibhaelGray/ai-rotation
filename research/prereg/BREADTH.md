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

## Result (2026-10-25): 0 of 4 pass

| signal | score | S&P sub-industries 4w / 13w | S&P sectors 4w / 13w | AI layers 4w / 13w |
|---|---|---|---|---|
| participation | −0.42 | −1.15 / −0.55 | −1.16 / −0.76 | +0.28 / +0.82 |
| participation_change | −0.35 | −0.45 / −0.30 | −0.11 / −0.57 | −0.81 / +0.14 |
| narrow_leadership | −0.13 | +0.22 / +0.27 | −0.51 / −0.33 | −0.14 / −0.30 |
| net_new_highs | −0.30 | −0.65 / −0.55 | −0.57 / −0.50 | +0.22 / +0.23 |

**Reading.**
- **The classic breadth warning does not hold in S&P baskets; the reverse shows instead.**
  When most of a basket's members are above their 50-day averages, or making new highs, the
  basket tends to *under*perform over the next 4-13 weeks. At 4 weeks that sits at about the
  95th percentile of noise. Breadth there behaves like a short-term overbought reading.
- **Narrow leadership predicts nothing.**
- **Only the AI layers show the classic direction:** good participation is followed by
  outperformance at 13 weeks (+0.82), too weak to pass and opposite to the S&P baskets.
