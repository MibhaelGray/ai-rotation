import numpy as np
import pandas as pd

NAME = "volume-conditioned pullback + continuity 26s4"
IDEA = "Frog-in-pan 26s4 relative momentum + continuity, plus a 4w reversal leg weighted up when the recent move came on low dollar volume vs own history and down on heavy volume."


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
    cont = -np.sign(mom) * (neg_f - pos_f)

    v = bars.volume.reindex(index=px.index, columns=px.columns)
    c = bars.close.reindex(index=px.index, columns=px.columns)
    dv = (v * c)
    dv = dv.where(dv > 0)
    dv_recent = dv.rolling(4, min_periods=3).mean()
    dv_base = dv.shift(4).rolling(26, min_periods=20).mean()
    vsurp = np.log(dv_recent / dv_base)

    valid = mom.notna() & rev.notna() & cont.notna()
    mom = mom.where(valid)
    rev = rev.where(valid)
    cont = cont.where(valid)
    vsurp = vsurp.where(valid)

    r_mom = mom.rank(axis=1, pct=True) - 0.5
    r_rev = rev.rank(axis=1, pct=True) - 0.5
    r_cont = cont.rank(axis=1, pct=True) - 0.5
    vr = vsurp.rank(axis=1, pct=True)
    w = (1.5 - vr).fillna(1.0)
    out = r_mom + r_cont + r_rev * w
    return out.reindex_like(px)
