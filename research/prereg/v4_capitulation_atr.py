"""Pre-registered 2026-10-25, ATR and volume batch, test V4. See research/prereg/README.md.
Scored once; never edited."""
import numpy as np
import pandas as pd

NAME = "V4 capitulation: 20d relative loss scaled by ATR expansion"
IDEA = ("For names that fell hard against the benchmark over 20 days while their 10-day ATR expanded "
        "against its 60-day level: a volatile selloff marks seller exhaustion and a rebound.")

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
    loss = -np.log(rs / rs.shift(20))
    expansion = atr(c, h, l, 10) / atr(c, h, l, 60)
    return weekly(loss * expansion, px)
