"""Pre-registered 2026-10-25, test Q3. See research/prereg/README.md. Scored once; never edited."""
import numpy as np
import pandas as pd

NAME = "Q3 pullback-in-trend within Lagging and Improving"
IDEA = ("Among names left of centre (Lagging or Improving) only, for a steady 26w-skip-4w relative "
        "trend that dipped over the last 4 weeks: a pullback in an intact trend marks a bottom.")

def quadrant(px, bench):
    """The page's weekly RRG quadrant: 0 Leading, 1 Weakening, 2 Lagging, 3 Improving."""
    sm = (100 * px.div(bench, axis=0)).ewm(span=3, adjust=False).mean()
    rsr = 100 * sm / sm.rolling(10).mean()
    rsm = (100 * rsr / rsr.shift(1)).ewm(span=3, adjust=False).mean()
    q = np.where(rsr >= 100, np.where(rsm >= 100, 0, 1), np.where(rsm >= 100, 3, 2)).astype(float)
    return pd.DataFrame(q, index=px.index, columns=px.columns).where(rsr.notna() & rsm.notna())


def rel_daily(px, bench, bars):
    d = bars.daily.close
    return np.log(d[px.columns].div(d[bench.name], axis=0)).diff()


def weekly(f, px):
    return f.reindex(px.index, method="ffill").where(px.notna())


def signal(px, bench, bars):
    rs = px.div(bench, axis=0)
    vol = np.log(rs).diff().rolling(26, min_periods=20).std()
    left = quadrant(px, bench).isin([2, 3])
    mom = (np.log(rs.shift(4) / rs.shift(26)) / vol).where(left)
    pullback = (-np.log(rs / rs.shift(4))).where(left)
    ok = mom.notna() & pullback.notna()
    rank = lambda f: f.where(ok).rank(axis=1, pct=True)
    return ((rank(mom) + rank(pullback)) / 2).where(ok)
