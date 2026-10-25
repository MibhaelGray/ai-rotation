# Overnight research report (2026-10-25)

**Goal:** find technical signals that anticipate when a factor rotates up or down.

**Bottom line:** nothing passed the final out-of-sample test. One effect kept the right sign
almost everywhere: factors with steady, low-skew returns that lagged recently go on to
outperform. It is too weak to trade on its own, and it does not show up in the AI stocks or
layers after 2022. One AI-specific lead, the bear-market rebound below, is worth tracking
forward.

## How it was kept honest

- **Plans committed first.** Every test's rules, universes and pass bar were committed to
  git before it ran (`research/prereg/`), and every result was recorded in the next commit,
  pass or fail.
- **Large searches were split in time.** Combinations were screened on 1999-2010,
  shortlisted, then scored once on 2011-2022 (and on AI stocks/layers discovery never saw),
  with the bar adjusted for every candidate validated on those years.
- **The 2023+ holdout was used only by the rules.** Skewness alone went there after passing
  on independent universes. The final consensus signal went there once, across 8 universes.
- **Volume of testing.** 46,887 combinations were screened in discovery. 42 distinct
  signals are in the main log (bar now 1.65), and 100 shortlisted candidates were validated.

## Rounds

| # | Test | Result |
|---|---|---|
| 1 | Search: 13,575 combinations (1-3 of 30 features × all/right/left of the RRG centre), ETFs | 0/20 validated. Every shortlisted candidate was built on low skew; about a quarter of discovery strength survived |
| 2 | Same, in bull vs bear markets | 0/20. Low skew works on ETFs in bull markets; illiquid AI stocks rebound in bear markets |
| 3 | Macro trends (rates, curve, dollar, oil, VIX tilts) | 0/6. Oil and VIX tilts reverse (negative in all cells) |
| 4 | Calendar seasonality | 0/2. Nothing |
| 5 | Timing a factor against its own history | 0/20. Collapsed to about zero out of sample |
| 6 | Skewness alone on 32 country + 29 style ETFs | **PASS** (+1.22 vs 1.14). Holdout: fail (+0.42 vs 1.00), but positive in all 6 cells |
| 7 | Breadth on S&P sub-industry/sector baskets + AI layers | 0/4. Broad participation comes before *under*performance in S&P baskets |
| 8 | Bear-market illiquidity on S&P 500 stocks | **PASS** (+2.41), but survivorship-inflated. On 2023+ it vanishes on S&P stocks and holds on AI stocks |
| 9 | Search: 19,737 combinations on constituent-built baskets | 0/20. Best (low skew + 1w losers + falling RS-Momentum) positive in all 6 cells incl. AI layers, +0.87 vs 1.57 |
| Final | Low skew + 1w losers, one shot on all 8 universes' 2023+ | Fail (+0.28 vs 1.00). Positive in 13/16 cells, nothing on AI stocks or layers |

Earlier in the night, outside the rounds above: ATR and volume on their own (0/4), return
signals within quadrants (0/3), the near-miss equal-thirds combo on new universes (fail), and
the regime backtester (quadrant forecasts improve at 4 weeks but don't pay).

## What is probably real, and how big

- **Low skewness (steady rather than spiky gains) → later outperformance.**
  - The right sign in 1999-2010, 2011-2022 and 2023+, and on US ETFs, country ETFs, style
    ETFs and S&P baskets.
  - The rank IC is about 0.03-0.09, with a net spread of about +1% per quarter on ETFs.
  - It is absent in AI stocks.
- **AI stocks in QQQ drawdowns:** illiquid, low-skew names that fell last week rebound over
  the next quarter.
  - 2011-2022 validation ratio +2.84 at 13 weeks; 2023+ mean IC +0.12 at 13 weeks.
  - It rests on only about 8 drawdown episodes in total. A lead, not proven.

## What is not real (on this data)

- **Forecasting the next quadrant** helps a little at 4 weeks, but it predicts the chart,
  not prices.
- **RRG momentum and quadrant changes** do not predict returns.
- **Breadth as a top warning** fails: in S&P baskets broad participation is a short-term
  overbought sign.
- **ATR, volume, macro trends, seasonality and timing a factor against its own history**
  show nothing consistent.

## Why the search stopped before 10am

Every family of price, volume, breadth, macro and calendar idea available in free daily
data has now been tested with a committed rule, and both the research period and the
holdout are used up. More combinations on the same data would only buy lottery tickets: the
discovery-to-validation shrinkage tonight (t of about 4 falling to about 1.5) shows how much
of a search's best result is luck. Real progress needs either:

1. **New data** that daily prices don't contain: fund flows, short interest, options
   positioning, earnings revisions, all of which need a paid source.
2. **Time.** `research/forward.py` snapshots the leads' picks each week.
   - Run it weekly: `python research/forward.py --refresh`, then commit the snapshot.
   - Grade it with `python research/forward.py --score`.
   - The first snapshot (2026-10-23) is committed. The AI bear-rebound lead is inactive
     until QQQ falls below its 40-week average.

All files are in `research/`: `prereg/*.md` for each plan and result, `search/*` for
discovery and validation logs, and `log.jsonl`, `confirm_log.jsonl`, `holdout_log.jsonl`
and `final_log.jsonl`.

## Addendum: small and mid caps, and a survivorship lesson

Run after the report above (`prereg/SMALLCAP.md`), on about 1,000 S&P 400 and 600 stocks
that nothing had been scored on.

- **The bear-market rebound first looked like the project's first real signal.** It scored
  +3.32 on 1999-2022 and +1.37 on 2023+, net of costs, with every year right.
- **Then the survivorship check removed it.** Rebuilt with point-in-time index membership,
  meaning the 312 stocks removed since 2023 were put back, the 2023+ score fell to **+0.34**
  and failed. Even that correction flatters the signal, because 430 removed names have no
  Yahoo data.
- **The lesson.** Any stock-level result on today's member lists is suspect, the AI baskets
  included, since they were chosen in 2026 from survivors. The AI bear-rebound lead should be
  treated as probably survivorship. ETFs have no such problem within a fund, which is why low
  skewness on ETFs is the more trustworthy of the night's two findings.
- **The other small/mid-cap tests failed.** Low skew + 1w losers was positive in all 8 cells
  on 2023+ but scored +0.77 against a bar of 1.00.
