"""Pre-registered 2026-10-25, test Q2. See research/prereg/README.md. Scored once; never edited."""
import numpy as np
import pandas as pd

NAME = "Q2 skewness within Leading"
IDEA = ("Among names in the Leading quadrant only, against right-skewed daily relative returns "
        "over 126 days: leadership built on a few jumps rather than steady gains rolls over.")

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
    skew = -weekly(rel_daily(px, bench, bars).rolling(126, min_periods=90).skew(), px)
    return skew.where(quadrant(px, bench) == 0)
