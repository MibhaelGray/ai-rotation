"""The one file a research run may edit. See research/RULES.md.

signal(px, bench, bars) returns a frame shaped like px. Higher must mean "expected to
outperform the benchmark over the next 1-3 months". See RULES.md for the full contract.
Only information up to and including each row's date may be used.
"""
import numpy as np
import pandas as pd

NAME = "skewness + lottery + pullback-in-trend, equal thirds"
IDEA = ("Equal-weight rank-sum of three logged ideas, weights fixed in advance, not tuned: against "
        "right-skewed names (126d), against the biggest one-day spike (21d), and for a steady "
        "26w-skip-4w relative trend that dipped last month.")


def signal(px: pd.DataFrame, bench: pd.Series, bars) -> pd.DataFrame:
    d = bars.daily.close
    rel = np.log(d[px.columns].div(d[bench.name], axis=0)).diff()
    wk = lambda f: f.reindex(px.index, method="ffill").where(px.notna())
    skew = -wk(rel.rolling(126, min_periods=90).skew())
    lottery = -wk(rel.rolling(21, min_periods=15).max())

    rs = px.div(bench, axis=0)
    vol = np.log(rs).diff().rolling(26, min_periods=20).std()
    mom = np.log(rs.shift(4) / rs.shift(26)) / vol
    pullback = -np.log(rs / rs.shift(4))

    rank = lambda f: f.rank(axis=1, pct=True)
    trend = (rank(mom) + rank(pullback)) / 2
    ok = skew.notna() & lottery.notna() & mom.notna() & pullback.notna()
    return (rank(skew) + rank(lottery) + trend).where(ok)
