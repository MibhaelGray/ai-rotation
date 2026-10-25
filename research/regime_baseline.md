# Regime baseline (research period, before 2023)

How well the RRG alone forecasts the quadrant H weeks ahead, out of sample. A candidate must
beat the RRG model's log loss. Lower log loss is better; accuracy is the share of correct calls.

| universe | H | factors | weeks | log loss: climatology | RRG model | accuracy: stays put | RRG model |
|---|---|---|---|---|---|---|---|
| AI layers vs QQQ | 4 | 31 | 200 | 1.354 | 1.082 | 32.5% | 49.3% |
| AI layers vs QQQ | 13 | 31 | 182 | 1.352 | 1.368 | 27.7% | 32.3% |
| AI subsectors vs QQQ | 4 | 82 | 200 | 1.357 | 1.072 | 31.5% | 49.9% |
| AI subsectors vs QQQ | 13 | 82 | 182 | 1.357 | 1.364 | 26.0% | 31.7% |
| ETFs vs SPY | 4 | 43 | 1129 | 1.356 | 1.075 | 31.8% | 48.9% |
| ETFs vs SPY | 13 | 43 | 1111 | 1.356 | 1.362 | 26.4% | 31.6% |
| AI stocks vs QQQ | 4 | 278 | 200 | 1.359 | 1.068 | 31.3% | 50.1% |
| AI stocks vs QQQ | 13 | 278 | 182 | 1.359 | 1.362 | 26.4% | 30.5% |

## Where a quadrant goes in 4 weeks (row = now, column = 4 weeks later)

**AI layers vs QQQ**

| now \ in 4w | Leading | Weakening | Lagging | Improving |
|---|---|---|---|---|
| Leading | 36% | 42% | 21% | 1% |
| Weakening | 29% | 30% | 38% | 3% |
| Lagging | 24% | 1% | 34% | 41% |
| Improving | 47% | 3% | 25% | 25% |

**AI subsectors vs QQQ**

| now \ in 4w | Leading | Weakening | Lagging | Improving |
|---|---|---|---|---|
| Leading | 34% | 42% | 23% | 1% |
| Weakening | 27% | 28% | 41% | 3% |
| Lagging | 24% | 1% | 34% | 41% |
| Improving | 45% | 4% | 26% | 26% |

**ETFs vs SPY**

| now \ in 4w | Leading | Weakening | Lagging | Improving |
|---|---|---|---|---|
| Leading | 35% | 42% | 23% | 1% |
| Weakening | 28% | 27% | 42% | 3% |
| Lagging | 23% | 1% | 35% | 42% |
| Improving | 45% | 3% | 26% | 27% |

**AI stocks vs QQQ**

| now \ in 4w | Leading | Weakening | Lagging | Improving |
|---|---|---|---|---|
| Leading | 32% | 42% | 25% | 1% |
| Weakening | 26% | 27% | 43% | 3% |
| Lagging | 22% | 1% | 35% | 42% |
| Improving | 43% | 3% | 26% | 28% |
