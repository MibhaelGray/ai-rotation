"""Survivorship check of the small/mid-cap bear rebound on 2023+. Rules: research/prereg/SMALLCAP.md.

  python research/smallcap_surv.py

The S&P 400 and 600 stock universes are rebuilt with point-in-time membership from
Wikipedia's change logs: every stock removed since the log starts is added back up to its
removal date, and every add counts from its date. Removed stocks with no Yahoo history
(mostly acquisitions) stay missing; the run reports how many.
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


SC = load_file("smallcap", HERE / "smallcap.py")
ev, bt = SC.ev, SC.bt
LOG = HERE / "smallcap_surv_log.jsonl"
EXTRA = ev.CACHE / "sp400_600_removed_ohlcv.pkl"
NAME = "bear rebound: skew + 1w reversal + illiquidity"


def membership(key, current, closes):
    """Point-in-time member mask for one index from its add and remove events."""
    adds = pd.read_csv(ev.CACHE / "sp400_600_adds.csv", parse_dates=["date"])
    rem = pd.read_csv(ev.CACHE / "sp400_600_removals.csv", parse_dates=["date"])
    ev_ = pd.concat([adds[adds["index"] == key].assign(kind=1)[["ticker", "date", "kind"]],
                     rem[rem["index"] == key].rename(columns={"rem": "ticker"}).assign(kind=-1)[["ticker", "date", "kind"]]])
    mask = pd.DataFrame(False, index=closes.index, columns=closes.columns)
    for t in closes.columns:
        e = ev_[ev_.ticker == t].dropna(subset=["date"]).sort_values("date")
        state = t in current if e.empty else e.kind.iloc[0] == -1    # before its first event
        last = closes.index[0]
        for d, k in zip(e.date, e.kind):
            mask.loc[(mask.index >= last) & (mask.index < d), t] = state
            state, last = k == 1, d
        mask.loc[mask.index >= last, t] = state
    return mask


def main():
    if ev.read_log(LOG):
        sys.exit("the survivorship check already ran; one-shot")
    rem = pd.read_csv(ev.CACHE / "sp400_600_removals.csv")
    raw = pd.read_pickle(ev.CACHE / "sp400_600_ohlcv.pkl")
    need = sorted(set(rem.rem) - set(raw["Close"].columns))
    if not EXTRA.exists():
        pd.to_pickle(ev.ohlcv(need, "max"), EXTRA)
    extra = pd.read_pickle(EXTRA)
    d = {f: pd.concat([raw[f], extra[f]], axis=1) for f in ["Close", "High", "Low", "Volume"]}
    d = {f: x.loc[:, ~x.columns.duplicated()] for f, x in d.items()}
    d = {f: x[x.index >= "1999-01-01"] for f, x in d.items()}
    found = [t for t in need if t in d["Close"] and d["Close"][t].notna().any()]
    print(f"removed tickers not in the original download: {len(need)}, with Yahoo history: {len(found)}")
    spec, _ = SC.TESTS[NAME]
    U = []
    for label, (key, bench) in SC.INDEXES.items():
        current = set(pd.read_csv(ev.CACHE / f"{key}_members.csv").ticker)
        removed = set(rem[rem["index"] == key].rem)
        names = [t for t in sorted(current | removed) if t in d["Close"] and d["Close"][t].notna().any()]
        m = membership(key, current, d["Close"][names])
        md = ev.Bars(*(d[f][names].where(m).assign(**{bench: d[f][bench]}) for f in ["Close", "High", "Low", "Volume"]))
        px = bt.weekly(md.close)
        bars = ev.weekly_bars(md.close, md.high, md.low, md.volume, px.index)
        in23 = m[m.index >= "2023-01-01"].any()
        print(f"{label}: {in23.sum()} stocks were members at some point since 2023 "
              f"({len(set(in23[in23].index) - current)} of them since removed)")
        U.append((f"{label} stocks vs {bench} (point-in-time)", px, bars, names, bench, 50))
    cells = ev.score_cells(SC.make(spec), U, "holdout")
    v = ev.verdict(cells, 1)
    if v["passed"] and v["score"] < 0:
        v.update(passed=False, why="clears the bar in the wrong direction")
    with open(LOG, "a") as f:
        f.write(json.dumps(dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), name=NAME, spec=spec, found=len(found),
                                missing=len(need) - len(found), **v, cells=cells)) + "\n")
    ev.show(f"{NAME}  [2023+, point-in-time membership]", cells, v)


if __name__ == "__main__":
    main()
