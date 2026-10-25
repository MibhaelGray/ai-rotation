"""Breadth signals on baskets built from their constituents. Rules: research/prereg/BREADTH.md.

  python research/breadth.py            score each signal once, logged to log.jsonl

Universes (each basket an equal-weight daily index of its members, as the page builds the AI
layers):
  S&P sub-industries vs SPY   GICS sub-industries of today's S&P 500 with 3+ members,
                              each stock counted only from the date it joined the index
  S&P sectors vs SPY          the 11 GICS sectors, built the same way
  AI layers vs QQQ            the page's 31 AI layers

Breadth needs members, which the ETF universes do not have. Every signal here describes how
many of a basket's members take part in its move.
"""
import hashlib, importlib.util, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != HERE]
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


R = load_file("regime", HERE / "regime.py")
ev, bt = R.ev, R.bt
MIN_MEMBERS = 3
SIGNALS = ["participation", "participation_change", "narrow_leadership", "net_new_highs"]


def sp500():
    m = pd.read_csv(ev.CACHE / "sp500_members.csv")
    raw = pd.read_pickle(ev.CACHE / "sp500_ohlcv.pkl")
    d = {f: raw[f][raw[f].index >= "1999-01-01"] for f in ["Close", "High", "Low", "Volume"]}
    md = ev.Bars(d["Close"].copy(), d["High"].copy(), d["Low"].copy(), d["Volume"].copy())
    for t, added in zip(m.ticker, pd.to_datetime(m.added, errors="coerce")):
        if t in md.close and pd.notna(added):           # a member counts only from the day it joined
            for f in [md.close, md.high, md.low, md.volume]:
                f.loc[f.index < added, t] = np.nan
    have = set(md.close.columns[md.close.notna().any()])
    sub = {k: sorted(set(g.ticker) & have) for k, g in m.groupby("sub")}
    sec = {k: sorted(set(g.ticker) & have) for k, g in m.groupby("sector")}
    return md, {k: v for k, v in sub.items() if len(v) >= MIN_MEMBERS}, sec


def build(name, md, members, bench, min_n):
    C, H, L, V = R.basket_bars(md, members, min_members=2)
    rows = bt.weekly(C.assign(**{bench: md.close[bench]}))
    close = C.assign(**{bench: md.close[bench]})
    bars = ev.weekly_bars(close, H.assign(**{bench: md.high[bench]}), L.assign(**{bench: md.low[bench]}),
                          V.assign(**{bench: md.volume[bench] * md.close[bench]}), rows.index)
    return (name, rows, bars, list(members), bench, min_n), md, members


def universes():
    md, sub, sec = sp500()
    ai = R.raw()["ai"]
    groups = R.raw()["groups"]
    layers = R.baskets(ai, groups, "layer")
    return [build("S&P sub-industries vs SPY", md, sub, "SPY", 10),
            build("S&P sectors vs SPY", md, sec, "SPY", 8),
            build("AI layers vs QQQ", ai, layers, "QQQ", 10)]


# ---------------------------------------------------------------- signals

def per_basket(P, members, f, how):
    out = {}
    for k in P.columns:
        x = f.reindex(columns=members[k])
        n = x.notna().sum(axis=1)
        out[k] = how(x).where(n >= MIN_MEMBERS)
    return pd.DataFrame(out).reindex(P.index, method="ffill").where(P.notna())


def make(name, md, members):
    c = md.close

    def signal(P, b, B):
        end = P.index[-1]
        cc = c.loc[:end]
        if name in ("participation", "participation_change"):
            ma = cc.rolling(50, min_periods=40).mean()
            above = (cc > ma).astype(float).where(ma.notna() & cc.notna())
            s = per_basket(P, members, above, lambda x: x.mean(axis=1))
            return s if name == "participation" else s - s.shift(4)
        if name == "narrow_leadership":
            r = np.log(cc / cc.shift(63))
            return -per_basket(P, members, r, lambda x: x.mean(axis=1) - x.median(axis=1))
        if name == "net_new_highs":
            hi = cc >= cc.rolling(252, min_periods=200).max()
            lo = cc <= cc.rolling(252, min_periods=200).min()
            ok = cc.rolling(252, min_periods=200).max().notna()
            net = (hi.astype(float) - lo.astype(float)).where(ok)
            return per_basket(P, members, net.rolling(5, min_periods=3).mean(), lambda x: x.mean(axis=1))
    return signal


def record(name):
    src = (HERE / "breadth.py").read_text() + f"\n# signal: {name}\n"
    return src, hashlib.sha256(src.encode()).hexdigest()[:12]


def main():
    U = universes()
    logged = {r["hash"] for r in ev.read_log(ev.LOG)}
    for name in SIGNALS:
        src, h = record(name)
        if h in logged:
            print(f"{name}: already scored")
            continue
        cells = []
        for tup, md, members in U:
            cells += ev.score_cells(make(name, md, members), [tup], "research")
        v = ev.verdict(cells, ev.n_trials(h))
        with open(ev.LOG, "a") as f:
            f.write(json.dumps(dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), mode="research", kind="candidate",
                                    name=f"B breadth: {name}", idea="basket breadth from constituents", hash=h, **v,
                                    cells=cells, source=src)) + "\n")
        ev.show(f"B breadth: {name}  [{h}, research]", cells, v)


if __name__ == "__main__":
    main()
