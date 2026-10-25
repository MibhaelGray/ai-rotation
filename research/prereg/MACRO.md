# Pre-registered: macro-trend rotation (2026-10-25)

Committed with `research/macro.py` before scoring. The signals passed the look-ahead check;
no returns were computed.

## Why

Everything tested so far used each fund's own prices. Sector rotation is often driven from
outside: rising yields lift banks, a falling dollar lifts materials and multinationals, oil
moves energy, and risk-off moves defensives. If macro trends persist and sector
sensitivities are stable, a fund exposed to a trending macro factor should keep
outperforming.

## Signals (higher = expected to outperform)

`beta × trend`, where:

- **beta** is the 104-week rolling regression slope of the fund's weekly log return relative
  to the benchmark on the factor's weekly change (at least 52 weeks);
- **trend** is the factor's change over the last 13 weeks.

| signal | factor (Yahoo) | change measured as |
|---|---|---|
| rates | 10-year Treasury yield (^TNX) | points |
| curve | 10-year minus 3-month yield (^TNX − ^IRX) | points |
| dollar | US dollar index (DX-Y.NYB) | log |
| oil | WTI crude futures (CL=F, from 2000-08) | log |
| vix | VIX (^VIX) | log |
| composite | mean percentile rank of the five above | — |

## Rules

- **Scoring.** Each is scored once on the frozen returns scorecard (research period, 6
  cells) and logged to `log.jsonl` as a normal trial, so the bar rises from about 1.60 to
  about 1.63.
- **Pass.** The standard verdict, with a positive direction expected.
- **Holdout.** A pass takes the one-shot holdout (`macro.py --holdout NAME`), as authorised.

## Known limits

- **Two macro factors move together.** Yields and the curve are correlated, so rates and
  curve are not independent tests.
- **Oil** starts in 2000, which costs the ETF universes their first year.
- **Betas are noisy,** and 104 weeks can straddle a regime change in how a sector responds.

## Result (2026-10-25): 0 of 6 pass

| signal | score | sign across the 6 cells |
|---|---|---|
| rates | −0.33 | mixed: negative on ETFs and sectors, positive on AI stocks |
| curve | −0.11 | mixed, near zero |
| dollar | +0.26 | positive in all six, but weak |
| oil | −0.61 | **negative in all six** |
| vix | −0.62 | **negative in all six** |
| composite | −0.44 | negative in all six |

**Reading.** The persistence hypothesis fails. For oil and VIX the effect is the reverse and
consistent: funds that gained from the factor's recent trend give it back over the next 1-3
months. That fits the reversal and overextension effects seen elsewhere, but at about −0.6
it is far below the bar. Writing a flipped version now would be a hypothesis chosen after
seeing the result, so it is noted and not tested.
