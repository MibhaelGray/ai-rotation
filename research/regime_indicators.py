"""Indicator library for the regime scorecard (research/regime.py). Add indicators here.

Each indicator is a function of one Universe `u` (see regime.Universe for what it holds)
returning a weekly frame shaped like u.px, or None when it cannot be computed for that
universe (breadth needs members). The sign does not matter: the model learns which way each
indicator points, separately in each quadrant. Use only past and current rows: rolling,
expanding and ewm windows and shift(k >= 0). The scorecard re-runs every indicator on
truncated data and rejects any whose past values change.

Every distinct indicator or combination scored raises the bar for the next, so add ideas
with a reason behind them, not parameter sweeps. Editing an indicator's code makes it a new
candidate.
"""
import numpy as np
import pandas as pd

REGISTRY = {}
R = None        # the regime module, set by regime.load_library


def ind(fn):
    REGISTRY[fn.__name__] = fn
    return fn


# ---------------------------------------------------------------- helpers

def own(u, f):
    return f.drop(columns=u.bench)


def rel_daily(u):
    """Daily log returns of each factor relative to the benchmark."""
    c = u.d.close
    return np.log(own(u, c).div(c[u.bench], axis=0)).diff()


def true_range(u):
    c, h, l = own(u, u.d.close), own(u, u.d.high), own(u, u.d.low)
    pc = c.shift(1)
    return np.maximum(h - l, np.maximum((h - pc).abs(), (l - pc).abs())).where(c.notna())


def weekly_rs(u):
    return u.px.div(u.b, axis=0)


def members_rrg(u):
    """Weekly closes and RRG of every member stock against the universe's benchmark."""
    if u.members is None:
        return None
    if not hasattr(u, "_mrrg"):
        mpx = R.weekly_last(u.md.close.drop(columns=u.bench), u.end).reindex(u.px.index)
        rsr, rsm, q = R.rrg(mpx, u.b)
        u._mrrg = mpx, rsr, rsm, q
    return u._mrrg


def per_basket(u, f, how):
    """Aggregate a member-level weekly frame into one column per basket."""
    return pd.DataFrame({k: how(f.reindex(columns=m)) for k, m in u.members.items()}).reindex(columns=u.px.columns)


# ---------------------------------------------------------------- RRG structure

@ind
def tenure(u):
    """Log of weeks the factor has spent in its current quadrant."""
    q = u.q
    run = q.ne(q.shift()).cumsum()
    out = pd.DataFrame({c: q[c].groupby(run[c]).cumcount() + 1 for c in q}).where(q.notna())
    return np.log(out)


@ind
def rrg_distance(u):
    """Distance from the chart's centre (how stretched the rotation is), in each factor's own units."""
    x, y = u.rsr - 100, u.rsm - 100
    sx = x.rolling(52, min_periods=26).std()
    sy = y.rolling(52, min_periods=26).std()
    return np.sqrt((x / sx) ** 2 + (y / sy) ** 2)


@ind
def rsr_z52(u):
    """RS-Ratio against its own last year: how unusual the current reading is for this factor."""
    m, s = u.rsr.rolling(52, min_periods=26).mean(), u.rsr.rolling(52, min_periods=26).std()
    return (u.rsr - m) / s


@ind
def curl(u):
    """Turning rate on the chart: change in heading over two weeks, + clockwise."""
    a = np.arctan2(u.rsm.diff(), u.rsr.diff())
    d = a.shift(2) - a
    return (d + np.pi) % (2 * np.pi) - np.pi


# ---------------------------------------------------------------- trend

@ind
def mom_26_4(u):
    """Vol-adjusted relative return from 26 to 4 weeks ago."""
    rs = weekly_rs(u)
    vol = np.log(rs).diff().rolling(26, min_periods=20).std()
    return np.log(rs.shift(4) / rs.shift(26)) / vol


@ind
def rev_4w(u):
    """Relative return over the last 4 weeks."""
    rs = weekly_rs(u)
    return np.log(rs / rs.shift(4))


@ind
def rs_52w_high(u):
    """Relative strength line against its own 52-week high (0 = at the high)."""
    rs = weekly_rs(u)
    return np.log(rs / rs.rolling(52, min_periods=40).max())


@ind
def rs_trend_40w(u):
    """Relative strength line against its 40-week average."""
    rs = weekly_rs(u)
    return np.log(rs / rs.rolling(40, min_periods=30).mean())


@ind
def price_trend_200d(u):
    """The factor's own price (not relative) against its 200-day average."""
    c = own(u, u.d.close)
    return u.weekly(np.log(c / c.rolling(200, min_periods=150).mean()))


@ind
def rsi_rs(u):
    """14-day RSI of the daily relative strength line."""
    r = rel_daily(u)
    up, dn = r.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean(), (-r.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    return u.weekly(100 - 100 / (1 + up / dn.replace(0, np.nan)))


# ---------------------------------------------------------------- return distribution

@ind
def skew126(u):
    """Skewness of daily relative returns over 126 days."""
    return u.weekly(rel_daily(u).rolling(126, min_periods=90).skew())


@ind
def lottery21(u):
    """Largest one-day relative return in the last 21 days."""
    return u.weekly(rel_daily(u).rolling(21, min_periods=15).max())


@ind
def vol_ratio(u):
    """Relative-return volatility over 20 days against 120 days."""
    r = rel_daily(u)
    return u.weekly(np.log(r.rolling(20, min_periods=15).std() / r.rolling(120, min_periods=90).std()))


# ---------------------------------------------------------------- range / ATR

@ind
def atr_stretch(u):
    """Distance of the close from its 50-day average, in 14-day ATRs."""
    c = own(u, u.d.close)
    return u.weekly((c - c.rolling(50, min_periods=40).mean()) / true_range(u).rolling(14, min_periods=10).mean())


@ind
def range_expansion(u):
    """10-day ATR against 60-day ATR, as a share of price."""
    tr = true_range(u) / own(u, u.d.close)
    return u.weekly(np.log(tr.rolling(10, min_periods=8).mean() / tr.rolling(60, min_periods=45).mean()))


@ind
def close_location(u):
    """Where closes sit in the day's range over 10 days (1 = at the highs, 0 = at the lows)."""
    c, h, l = own(u, u.d.close), own(u, u.d.high), own(u, u.d.low)
    loc = ((c - l) / (h - l).replace(0, np.nan))
    return u.weekly(loc.rolling(10, min_periods=7).mean())


@ind
def squeeze(u):
    """20-day high-low range in ATRs: low means a coiled, compressed market."""
    c, h, l = own(u, u.d.close), own(u, u.d.high), own(u, u.d.low)
    rng = h.rolling(20, min_periods=15).max() - l.rolling(20, min_periods=15).min()
    return u.weekly(np.log(rng / true_range(u).rolling(20, min_periods=15).mean()))


# ---------------------------------------------------------------- volume

@ind
def rel_volume(u):
    """10-day average volume against 120-day."""
    v = own(u, u.d.volume).replace(0, np.nan)
    return u.weekly(np.log(v.rolling(10, min_periods=7).mean() / v.rolling(120, min_periods=90).mean()))


@ind
def updown_volume(u):
    """Volume on relative up days against relative down days, 20 days."""
    r, v = rel_daily(u), own(u, u.d.volume)
    up = v.where(r > 0, 0).rolling(20, min_periods=15).sum()
    dn = v.where(r < 0, 0).rolling(20, min_periods=15).sum()
    return u.weekly(np.log((up + 1) / (dn + 1)).where(r.notna()))


@ind
def climax(u):
    """Volume climaxes in the last 20 days: up-climax days minus capitulation days.

    A climax day is a relative move beyond 2 standard deviations (60-day) on volume over 1.5x
    its 50-day average."""
    r, v = rel_daily(u), own(u, u.d.volume)
    big = r.abs() > 2 * r.rolling(60, min_periods=45).std().shift(1)
    heavy = v > 1.5 * v.rolling(50, min_periods=40).mean().shift(1)
    s = (np.sign(r) * (big & heavy)).rolling(20, min_periods=15).sum()
    return u.weekly(s.where(r.notna()))


# ---------------------------------------------------------------- breadth (baskets only)

@ind
def breadth_rsr(u):
    """Share of the basket's stocks right of centre (RS-Ratio >= 100) against the same benchmark."""
    m = members_rrg(u)
    if m is None:
        return None
    rsr = m[1]
    return per_basket(u, (rsr >= 100).astype(float).where(rsr.notna()), lambda f: f.mean(axis=1))


@ind
def breadth_change(u):
    """4-week change in the share of the basket's stocks right of centre."""
    b = breadth_rsr(u)
    return None if b is None else b - b.shift(4)


@ind
def breadth_leading(u):
    """Share of the basket's stocks in the Leading quadrant."""
    m = members_rrg(u)
    if m is None:
        return None
    q = m[3]
    return per_basket(u, (q == 0).astype(float).where(q.notna()), lambda f: f.mean(axis=1))


@ind
def above_50d(u):
    """Share of the basket's stocks above their own 50-day average."""
    if u.members is None:
        return None
    c = u.md.close.drop(columns=u.bench)
    a = (c > c.rolling(50, min_periods=40).mean()).astype(float).where(c.rolling(50, min_periods=40).mean().notna())
    return per_basket(u, a.reindex(u.px.index, method="ffill"), lambda f: f.mean(axis=1))


@ind
def dispersion(u):
    """Cross-sectional spread of the basket's stocks' 4-week returns."""
    m = members_rrg(u)
    if m is None:
        return None
    r = np.log(m[0] / m[0].shift(4))
    return per_basket(u, r, lambda f: f.std(axis=1).where(f.notna().sum(axis=1) >= 3))


@ind
def narrow_leadership(u):
    """Best stock's 4-week return minus the basket median: one name carrying the basket."""
    m = members_rrg(u)
    if m is None:
        return None
    r = np.log(m[0] / m[0].shift(4))
    return per_basket(u, r, lambda f: (f.max(axis=1) - f.median(axis=1)).where(f.notna().sum(axis=1) >= 3))
