import numpy as np
import pandas as pd

NAME = "52w-high anchor skip4 + continuity + pullback"
IDEA = "Rank-sum of vol-scaled distance of the relative ratio (lagged 4w) from its 52w high, frog-in-pan continuity of the 26s4 trend, and negative last-4w relative return: anchored, smooth relative trends with a recent dip outperform."


def signal(px: pd.DataFrame, bench: pd.Series, bars) -> pd.DataFrame:
    rs = px.div(bench, axis=0)
    lr = np.log(rs.where(rs > 0))
    dlr = lr.diff()
    vol = dlr.rolling(26, min_periods=20).std()
    vol = vol.where(vol > 0)
    lr4 = lr.shift(4)
    hi52 = lr4.rolling(52, min_periods=40).max()
    prox = (lr4 - hi52) / (vol * np.sqrt(13.0))
    mom = lr4 - lr.shift(26)
    rev = -(lr - lr4) / (vol * 2.0)
    have = dlr.notna()
    pos = (dlr > 0).astype(float).where(have)
    neg = (dlr < 0).astype(float).where(have)
    pos_f = pos.shift(4).rolling(22, min_periods=18).mean()
    neg_f = neg.shift(4).rolling(22, min_periods=18).mean()
    cont = -np.sign(mom) * (neg_f - pos_f)
    valid = prox.notna() & rev.notna() & cont.notna()
    prox = prox.where(valid)
    rev = rev.where(valid)
    cont = cont.where(valid)
    r_prox = prox.rank(axis=1, pct=True) - 0.5
    r_rev = rev.rank(axis=1, pct=True) - 0.5
    r_cont = cont.rank(axis=1, pct=True) - 0.5
    out = r_prox + r_rev + r_cont
    return out.reindex_like(px)
