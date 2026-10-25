import numpy as np
import pandas as pd

NAME = "frog-in-pan continuity + pullback 26s4"
IDEA = "Rank-sum of vol-adjusted 26w-skip4 relative momentum, its path continuity (negative information discreteness over the same window), and negative last-4w relative return: smooth relative trends with a recent pullback outperform."


def signal(px: pd.DataFrame, bench: pd.Series, bars) -> pd.DataFrame:
    rs = px.div(bench, axis=0)
    lr = np.log(rs.where(rs > 0))
    dlr = lr.diff()
    vol = dlr.rolling(26, min_periods=20).std()
    vol = vol.where(vol > 0)
    mom = (lr.shift(4) - lr.shift(26)) / (vol * np.sqrt(22.0))
    rev = -(lr - lr.shift(4)) / (vol * 2.0)
    have = dlr.notna()
    pos = (dlr > 0).astype(float).where(have)
    neg = (dlr < 0).astype(float).where(have)
    pos_f = pos.shift(4).rolling(22, min_periods=18).mean()
    neg_f = neg.shift(4).rolling(22, min_periods=18).mean()
    info_disc = np.sign(mom) * (neg_f - pos_f)
    cont = -info_disc
    valid = mom.notna() & rev.notna() & cont.notna()
    mom = mom.where(valid)
    rev = rev.where(valid)
    cont = cont.where(valid)
    r_mom = mom.rank(axis=1, pct=True) - 0.5
    r_rev = rev.rank(axis=1, pct=True) - 0.5
    r_cont = cont.rank(axis=1, pct=True) - 0.5
    out = r_mom + r_rev + r_cont
    return out.reindex_like(px)
