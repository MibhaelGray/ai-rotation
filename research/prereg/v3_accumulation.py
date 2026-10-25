"""Pre-registered 2026-10-25, ATR and volume batch, test V3. See research/prereg/README.md.
Scored once; never edited."""
import numpy as np
import pandas as pd

NAME = "V3 accumulation: volume on relative up days vs down days, 50d"
IDEA = ("For names whose volume comes on days they beat the benchmark rather than on days they lag it: "
        "accumulation by buyers precedes outperformance.")

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
    r = np.log(rs).diff()
    up = v.where(r > 0, 0).rolling(50, min_periods=40).sum()
    dn = v.where(r < 0, 0).rolling(50, min_periods=40).sum()
    return weekly(np.log((up + 1) / (dn + 1)).where(r.notna() & v.notna()), px)
