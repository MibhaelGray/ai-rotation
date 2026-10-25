import numpy as np
import pandas as pd

NAME = "pullback within relative trend 26s4 + rev4"
IDEA = "Cross-sectional rank of vol-adjusted 26w-skip4 relative momentum plus rank of the negative vol-adjusted last-4w relative return: buy pullbacks in relative uptrends, fade bounces in downtrends."


def signal(px: pd.DataFrame, bench: pd.Series, bars) -> pd.DataFrame:
    rs = px.div(bench, axis=0)
    lr = np.log(rs.where(rs > 0))
    vol = lr.diff().rolling(26, min_periods=20).std()
    vol = vol.where(vol > 0)
    mom = (lr.shift(4) - lr.shift(26)) / (vol * np.sqrt(22.0))
    rev = -(lr - lr.shift(4)) / (vol * 2.0)
    valid = mom.notna() & rev.notna()
    mom = mom.where(valid)
    rev = rev.where(valid)
    r_mom = mom.rank(axis=1, pct=True) - 0.5
    r_rev = rev.rank(axis=1, pct=True) - 0.5
    out = r_mom + r_rev
    return out.reindex_like(px)
