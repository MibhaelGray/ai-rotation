"""Pre-registered 2026-10-25, ATR and volume batch, test V1. See research/prereg/README.md.
Scored once; never edited."""
import numpy as np
import pandas as pd

NAME = "V1 ATR overextension from the 50-day average"
IDEA = ("Against names stretched far above their 50-day average in 14-day ATRs, for names stretched "
        "below it: moves measured in their own volatility units mean-revert over 1-3 months.")

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
    stretch = (c - c.rolling(50, min_periods=40).mean()) / atr(c, h, l, 14)
    return -weekly(stretch, px)
