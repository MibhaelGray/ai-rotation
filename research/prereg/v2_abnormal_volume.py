"""Pre-registered 2026-10-25, ATR and volume batch, test V2. See research/prereg/README.md.
Scored once; never edited."""
import numpy as np
import pandas as pd

NAME = "V2 abnormal volume 20d vs 250d"
IDEA = ("For names trading on unusually heavy volume against their own past year: the high-volume "
        "return premium, where attention brings new buyers and outperformance follows.")

def daily(px, bench, bars):
    """Daily close, high, low and volume of the names, and their close relative to the benchmark."""
    d = bars.daily
    c, h, l = d.close[px.columns], d.high[px.columns], d.low[px.columns]
    v = d.volume[px.columns].replace(0, np.nan)
    return c, h, l, v, c.div(d.close[bench.name], axis=0)


def atr(c, h, l, n):
    pc = c.shift(1)
    tr = np.maximum(h - l, np.maximum((h - pc).abs(), (l - pc).abs())).where(c.notna())
    return tr.rolling(n, min_periods=int(n * 0.75)).mean()


def weekly(f, px):
    return f.reindex(px.index, method="ffill").where(px.notna())


def signal(px, bench, bars):
    c, h, l, v, rs = daily(px, bench, bars)
    return weekly(np.log(v.rolling(20, min_periods=15).mean() / v.rolling(250, min_periods=180).mean()), px)
