"""Forward test: record what tonight's leads pick now, and score past picks later.

  python research/forward.py            snapshot the leads' current rankings (once per week)
  python research/forward.py --score    score every past snapshot against what happened since

Nothing in the research period or the holdout can test these leads any further: both have
been used. Only data that does not exist yet can. Each snapshot is written to
research/forward/<date>.json and is meant to be committed, so its date proves it was made
before the outcome. --score compares each snapshot's ranking with the realised relative
returns over the 4 and 13 weeks after it, once those weeks have passed.

Leads (defined in research/prereg/, none of them passed a holdout):
  low_skew_losers   negative 126-day skewness + last week's laggards (FINAL.md), on the ETFs
                    and the S&P sector baskets, where its sign held on 2023+
  low_skew          negative 126-day skewness alone (CONFIRM_SKEW.md), on the ETFs
  ai_bear_rebound   skewness + 1-week reversal + illiquidity, only while QQQ is below its
                    40-week average (CONFIRM_STOCKS.md), on the AI stocks
Pass --refresh to re-download the ETF and AI price caches first, so the snapshot uses the
latest prices.
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
ev, bt = S.ev, S.bt
OUT = HERE / "forward"
LEADS = {
    "low_skew_losers": (S.make_signal(dict(features=[("skew126", -1), ("rev1", -1)], subset="all")), ["ETFs vs SPY"]),
    "low_skew": (S.make_signal(dict(features=[("skew126", -1)], subset="all")), ["ETFs vs SPY"]),
    "ai_bear_rebound": (SR.make_signal(dict(features=[("skew126", -1), ("rev1", -1), ("amihud", 1)], subset="bear")),
                        ["AI stocks vs QQQ"]),
}


def snapshot(refresh):
    OUT.mkdir(exist_ok=True)
    U = {u[0]: u for u in ev.load(refresh=refresh)}
    rec = dict(made=time.strftime("%Y-%m-%dT%H:%M:%S"), leads={})
    for lead, (fn, unis) in LEADS.items():
        for name in unis:
            _, px, bars, members, bench, _ = U[name]
            P, b, B = ev.panel(px, bars, members, bench, "holdout")     # all data, nothing cut
            s = fn(P, b, B).iloc[-1].dropna().sort_values(ascending=False)
            rec["leads"][f"{lead}|{name}"] = dict(asof=str(P.index[-1].date()), bench=bench,
                                                  ranking=[[t, round(float(v), 4)] for t, v in s.items()])
            top = ", ".join(s.index[:5]) if len(s) else "(no signal: condition not met)"
            print(f"{lead:<16} {name:<18} as of {P.index[-1].date()}: top {top}")
    path = OUT / f"{rec['leads'][next(iter(rec['leads']))]['asof']}.json"
    path.write_text(json.dumps(rec, indent=1))
    print(f"wrote {path.relative_to(HERE.parent)}; commit it so its date is on record")


def score():
    U = {u[0]: u for u in ev.load()}
    rows = []
    for path in sorted(OUT.glob("*.json")):
        rec = json.loads(path.read_text())
        for key, snap in rec["leads"].items():
            lead, name = key.split("|")
            _, px, _, _, bench, _ = U[name]
            asof = pd.Timestamp(snap["asof"])
            lr = np.log(px.div(px[bench], axis=0))
            for H in [4, 13]:
                if asof not in lr.index or lr.index.get_loc(asof) + H >= len(lr.index):
                    continue
                i = lr.index.get_loc(asof)
                fwd = (lr.iloc[i + H] - lr.iloc[i]).dropna()
                sig = pd.Series(dict(snap["ranking"]))
                both = sig.index.intersection(fwd.index)
                if len(both) < 5:
                    continue
                rows.append(dict(lead=lead, universe=name, asof=snap["asof"], H=H,
                                 ic=float(sig[both].rank().corr(fwd[both].rank()))))
    if not rows:
        print("no snapshot is old enough to score yet (4 weeks for the first result)")
        return
    df = pd.DataFrame(rows)
    print(df.groupby(["lead", "universe", "H"])["ic"].agg(["count", "mean", lambda x: (x > 0).mean()])
          .rename(columns={"<lambda_0>": "share positive"}).round(3))


if __name__ == "__main__":
    score() if "--score" in sys.argv else snapshot("--refresh" in sys.argv)
