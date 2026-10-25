# Regime research rules

The question: given where a factor sits on the RRG today, can technical indicators tell which
quadrant it will be in 4 or 13 weeks from now, better than the RRG can on its own, and do
those forecasts point the way prices actually go?

## Files

- `research/regime.py`: the scorecard. Frozen: changing it (universes, horizons, model,
  refit schedule, `HOLDOUT_START`) resets the experiment. Delete `regime_log.jsonl` and say so
  in the commit.
- `research/regime_indicators.py`: the indicator library. This is the file research edits.
  Each `@ind` function takes a Universe and returns a weekly frame (see its docstring).
- `research/regime_log.jsonl`: every candidate scored, with its source and hash. Never edited.
- `research/regime_baseline.md`: how well the RRG alone forecasts.

## Universes

| universe | factors | history | members (for breadth) |
|---|---|---|---|
| AI layers vs QQQ | 31 equal-weight baskets built from their stocks, as the page builds them | 2016- | yes |
| AI subsectors vs QQQ | 82 smaller baskets | 2016- | yes |
| ETFs vs SPY | 43 sector and industry ETFs | 1999- | no |
| AI stocks vs QQQ | 278 individual stocks | 2016- | no |

Quadrants are the page's weekly RRG: EMA 3, 10-week base, 1-bar momentum.

## The test

1. **Baseline model.** A multinomial logistic regression forecasts the quadrant H weeks ahead
   from the current quadrant, RS-Ratio and RS-Momentum (each per quadrant) and their one-week
   changes. That captures persistence and the clockwise rotation.
2. **Candidate model.** The same, plus each indicator interacted with the current quadrant,
   so an indicator can warn of tops in Leading without having to mean the same in Lagging.
3. **Walk-forward.** Both are refitted every 13 weeks on rows whose outcome was already known,
   after at least 2 years of history, and scored only on the weeks after each fit.
4. **Per cell** (universe x horizon):
   - **skill**: the baseline's log loss minus the candidate's, averaged per week, with a
     Newey-West t-stat
   - **payoff**: the rank IC between the candidate's shift in P(right of centre in H weeks)
     and the forward relative return
   - **years**: the share of calendar years in which skill was positive
5. **Verdict.**
   - **Score** is the mean skill t over the cells the indicator is defined in. It must be
     defined in at least 2 universes; breadth runs only on the two basket universes.
   - **Bar** is the one-sided Bonferroni z over all distinct candidates ever logged. It
     starts at 1.65 and passes 3.0 after about 30 candidates.
   - **FORECASTS:** score at or above the bar, skill positive in every cell, and positive in
     at least 60% of years.
   - **PAYS:** payoff IC positive in every cell.
   - **PASS** needs both.

`python research/regime.py --placebo 20` runs random-walk indicators through the same test
to check that noise does not pass.

## The holdout

`python research/regime.py --holdout --confirm a b` scores 2023 onward once per candidate,
and only for candidates already scored on the research period. Use it on finalists only.

## Known limits

- **Hindsight.** The AI baskets were chosen in 2026 and have about 6 research years, with
  roughly 4 of them scored out of sample. ETFs carry the long-history evidence.
- **Breadth** can only be tested on AI baskets, since there are no ETF holdings in the data.
- **Basket bars.** A basket's high and low are its index times its members' mean high/close
  and low/close, which approximates a true basket range.
- **Survivorship.** Today's members are applied to past prices, as on the page.

## Results so far (2026-10-25, research period only)

- **Noise check.** 20 random-walk indicators scored a mean of −2.2 and never rose above
  −1.5. Adding a useless indicator costs about 2 t-units of overfitting, so a score near −2
  means "no information", not "harmful".
- **The RRG alone.** At 4 weeks it gets about 49% of quadrants right, against 32% for
  "stays put". At 13 weeks it is no better than base rates (log loss 1.36 against 1.36):
  three months out, the quadrant cannot be forecast from the chart.
- **Singles (26).** None passes; the bar is now 2.9.
  - **4 weeks.** RSI of the daily RS line (t up to +13), distance from the chart's centre
    and RS-Ratio's z-score against its own year all sharpen the forecast in every universe.
    They read the same price data the weekly RRG smooths, only earlier, so they anticipate
    the indicator.
  - **13 weeks.** Every indicator sits at or below the noise level.
  - **Payoff.** None makes forecast changes that line up with forward relative returns.
  - **Breadth.** Helps a little at 4 weeks on subsectors (t +3.8) and not on layers.
- **Best three combined** (RSI of RS, distance, z-score): 4-week skill t of +3.6 to +11.8
  with accuracy up about 1 point, 13-week skill negative, payoff IC negative in every cell.
  It fails.

**Reading.** Short-term quadrant moves are partly forecastable, but that is forecasting the
indicator, not prices. Nothing tested anticipates the rotations that pay.
