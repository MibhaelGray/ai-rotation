# Pre-registered: confirm negative skewness alone on country and style ETFs (2026-10-25)

Committed before running. `python research/confirm_skew.py` runs it once.

## Why this one

Across everything tested tonight, negative skewness of daily relative returns (126 days) is
the one effect that kept its direction everywhere outside the AI stocks:

- **The full research period:** ETF and sector cell ratios of +1.2 to +2.1.
- **Round 1:** every shortlisted combination was built on it, and all of them stayed positive
  on ETFs and sectors in 2011-2022.
- **The equal-thirds confirmation:** IC was positive on the country and style ETFs.

It has never been scored alone on independent universes.

## Signal

`research/prereg/confirm_skew.py` is a byte-for-byte copy of the logged source, hash
`fe7bfe1142bc`.

## Universes and rules

- **Universes.** The ones in `research/confirm.py`, unchanged: 32 country ETFs against EFA
  and 29 US style ETFs against SPY. Research period only (before 2023); 4 cells.
- **Bar.** These universes were used once before (for the equal-thirds combo), so the bar is
  for 2 tests: z(1 − 0.05/4)/1.96 ≈ 1.14.
- **Pass.** Score ≥ 1.14, a positive IC in every cell, and the right direction in at least
  60% of years.
- **Holdout.** A pass takes the one-shot 2023+ holdout on the original universes
  (`evaluate.py --holdout --confirm research/prereg/confirm_skew.py`), as authorised. That
  holdout still includes the AI stocks, where skewness has shown no effect, so even a real
  ETF effect may fail there. That is accepted in advance.

## Result (run once, 2026-10-25): PASS

| cell | IC | IC t | placebo t95 | ratio | net spread per H | years right |
|---|---|---|---|---|---|---|
| Country ETFs vs EFA, 4w | +0.038 | +3.44 | 2.18 | +1.58 | +0.14% | 62% |
| Country ETFs vs EFA, 13w | +0.048 | +2.58 | 2.53 | +1.02 | +0.31% | 62% |
| US style ETFs vs SPY, 4w | +0.063 | +3.59 | 3.17 | +1.13 | +0.06% | 70% |
| US style ETFs vs SPY, 13w | +0.086 | +3.00 | 2.56 | +1.17 | +0.31% | 74% |

Score +1.22 against a bar of 1.14. Every cell is positive, the direction is right in 67% of
years, and the net spread after costs is positive in every cell. Per the rules above, it now
takes the one-shot 2023+ holdout on the original universes.
