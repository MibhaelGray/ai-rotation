# Pre-registered: round 9, combination search on constituent-built baskets (2026-10-25)

Committed with `research/search_baskets.py` before its discovery ran. Rounds 1-8 had already
been run when this was written.

## Why

This is the project's actual question, which factors rotate up or down, asked on a large set
of factor-like baskets built from members, the way the page builds the AI layers. Rounds 1
and 2 searched ETFs and stocks.

## Method

The same as search.py, with these differences:

- **Features.** search.py's 30 plus 4 breadth measures (participation, its 4-week change,
  narrow leadership, net new highs) from breadth.py. That gives 34, and 6,579 sets of 1-3.
  Each set is scored on all baskets and on those right or left of the RRG centre, for 19,737
  candidates. Directions come from discovery.
- **Discovery.** S&P sub-industry baskets (70) and S&P sector baskets (11), signal dates and
  outcomes before 2011.
- **Shortlist.** The 20 best with all 4 cells positive and a 0.9 overlap filter.
- **Validation.** Once, on 2011-2022, on the S&P sub-industry baskets, the S&P sector baskets
  and the AI layers (31), with the frozen scorecard's placebo-calibrated cells.

## Pass rule

- **Bar.** These baskets' 2011-2022 were already used by breadth.py's 4 signals, so the bar
  counts K = 24: z(1 − 0.05/48)/1.96, about 1.57.
- **Pass.** The scorecard verdict at that bar, in the same direction as discovery.
- **Holdout.** A pass goes to the holdout, as authorised. The S&P baskets have no formal
  holdout runner yet, so one would be written then without changing the signal; the AI layers
  can be scored on 2023+ directly.

## Known limits

- **Survivorship.** The baskets are built from today's S&P 500 members, each counted from
  its join date (see BREADTH.md).
