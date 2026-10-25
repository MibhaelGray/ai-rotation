"""Tonight's leads on S&P 400 (mid-cap) and S&P 600 (small-cap) stocks and baskets, never scored before.

  python research/smallcap.py           run every test once (research period and 2023+)

Rules: research/prereg/SMALLCAP.md. Universes:
  S&P 400 stocks vs MDY, S&P 600 stocks vs IJR
  S&P 400 sub-industry baskets vs MDY, S&P 600 sub-industry baskets vs IJR (3+ members,
  equal-weight daily index, as breadth.py builds them)
A stock added to its index inside Wikipedia's change log (S&P 400 from 2012, S&P 600 from
2019) counts only from its add date; earlier members have no date and count from the start.
"""
import importlib.util, json, sys, time
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


S = load_file("search", HERE / "search.py")
SR = load_file("search_regime", HERE / "search_regime.py")
Bm = load_file("breadth", HERE / "breadth.py")
ev, bt = S.ev, S.bt
LOG = HERE / "smallcap_log.jsonl"
INDEXES = {"S&P 400": ("sp400", "MDY"), "S&P 600": ("sp600", "IJR")}
TESTS = {
    "low skew": (dict(features=[("skew126", -1)], subset="all"), "all"),
    "low skew + 1w losers": (dict(features=[("skew126", -1), ("rev1", -1)], subset="all"), "all"),
    "bear rebound: skew + 1w reversal + illiquidity": (
        dict(features=[("skew126", -1), ("rev1", -1), ("amihud", 1)], subset="bear"), "stocks"),
    "skew + 1w losers + falling RS-Momentum": (
        dict(features=[("skew126", -1), ("rev1", -1), ("rs_mom", -1)], subset="all"), "baskets"),
}


def universes():
    raw = pd.read_pickle(ev.CACHE / "sp400_600_ohlcv.pkl")
    d = {f: raw[f][raw[f].index >= "1999-01-01"] for f in ["Close", "High", "Low", "Volume"]}
    adds = pd.read_csv(ev.CACHE / "sp400_600_adds.csv", parse_dates=["date"])
    out = []
    for label, (key, bench) in INDEXES.items():
        m = pd.read_csv(ev.CACHE / f"{key}_members.csv")
        have = [t for t in m.ticker if t in d["Close"] and d["Close"][t].notna().any()]
        cols = have + [bench]
        md = ev.Bars(*(d[f][cols].copy() for f in ["Close", "High", "Low", "Volume"]))
        for t, dt in adds[adds["index"] == key][["ticker", "date"]].itertuples(index=False):
            if t in md.close and pd.notna(dt):
                for f in [md.close, md.high, md.low, md.volume]:
                    f.loc[f.index < dt, t] = np.nan
        px = bt.weekly(md.close)
        bars = ev.weekly_bars(md.close, md.high, md.low, md.volume, px.index)
        out.append(("stocks", (f"{label} stocks vs {bench}", px, bars, have, bench, 50)))
        sub = {k: sorted(set(g.ticker) & set(have)) for k, g in m.groupby("sub")}
        sub = {k: v for k, v in sub.items() if len(v) >= Bm.MIN_MEMBERS}
        tup, _, _ = Bm.build(f"{label} sub-industries vs {bench}", md, sub, bench, 10)
        out.append(("baskets", tup))
    return out


def make(spec):
    return SR.make_signal(spec) if spec["subset"] in ("bull", "bear") else S.make_signal(spec)


def main():
    if ev.read_log(LOG):
        sys.exit("the small/mid-cap tests already ran; one-shot")
    U = universes()
    K = len(TESTS)
    for name, (spec, where) in TESTS.items():
        use = [tup for kind, tup in U if where == "all" or kind == where]
        rec = dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), name=name, spec=spec)
        for mode in ["research", "holdout"]:
            cells = ev.score_cells(make(spec), use, mode)
            v = ev.verdict(cells, K if mode == "research" else 1)
            if v["passed"] and v["score"] < 0:
                v.update(passed=False, why="clears the bar in the wrong direction")
            rec[mode] = dict(**v, cells=cells)
            ev.show(f"{name}  [{mode}{', bar for ' + str(K) + ' tests' if mode == 'research' else ', 2023+'}]", cells, v)
        with open(LOG, "a") as f:
            f.write(json.dumps(rec) + "\n")


if __name__ == "__main__":
    main()
