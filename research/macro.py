"""Macro-trend rotation signals on the frozen returns scorecard. Rules: research/prereg/MACRO.md.

  python research/macro.py            score every signal below once, logged to log.jsonl
  python research/macro.py --holdout NAME   one-shot 2023+ exam for a signal that passed

Idea: macro trends persist over a quarter, and a sector's sensitivity to a macro factor is
stable enough to estimate from its own past. So a fund whose relative returns rose with a
macro factor over the last two years should outperform while that factor keeps trending.

  signal = beta(fund's weekly relative return, weekly change in the factor, 104 weeks)
           x (change in the factor over the last 13 weeks)

Factors: 10-year yield (points), yield curve 10y minus 3m (points), dollar index, crude oil and
VIX (log changes). Each is scored alone, and their mean percentile rank is scored as a
composite. Each signal is one trial in log.jsonl under the usual rising bar.
"""
import hashlib, importlib.util, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != HERE]
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

spec = importlib.util.spec_from_file_location("evaluate", HERE / "evaluate.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

CACHE = ev.CACHE / "macro.pkl"
SYMBOLS = {"rates": "^TNX", "short": "^IRX", "dollar": "DX-Y.NYB", "oil": "CL=F", "vix": "^VIX"}
BETA_WEEKS, TREND_WEEKS = 104, 13
SIGNALS = ["rates", "curve", "dollar", "oil", "vix", "composite"]


def macro():
    if not CACHE.exists():
        import yfinance as yf
        d = yf.download(list(SYMBOLS.values()), period="max", interval="1d", progress=False, auto_adjust=True)["Close"]
        d.index = pd.to_datetime([str(i.date()) for i in d.index])
        pd.to_pickle(d, CACHE)
    d = pd.read_pickle(CACHE)
    lv = pd.DataFrame({k: d[s] for k, s in SYMBOLS.items()})
    lv["curve"] = lv["rates"] - lv["short"]
    return lv


def factor_changes(lv, index):
    """Weekly levels on the panel's rows (last close on or before each Friday) and their changes."""
    w = lv.ffill().reindex(index, method="ffill")
    out = {}
    for k in ["rates", "curve", "dollar", "oil", "vix"]:
        out[k] = w[k].diff() if k in ("rates", "curve") else np.log(w[k].where(w[k] > 0)).diff()
    return out, w


def tilt(P, b, lv, k):
    dm, w = factor_changes(lv, P.index)
    r = np.log(P.div(b, axis=0)).diff()
    x = dm[k]
    cov = r.rolling(BETA_WEEKS, min_periods=52).cov(x)
    beta = cov.div(x.rolling(BETA_WEEKS, min_periods=52).var(), axis=0)
    level = w[k] if k in ("rates", "curve") else np.log(w[k].where(w[k] > 0))
    trend = level - level.shift(TREND_WEEKS)
    return beta.mul(trend, axis=0)


def make(name, lv):
    def signal(P, b, B):
        if name != "composite":
            return tilt(P, b, lv, name)
        ranks = [tilt(P, b, lv, k).rank(axis=1, pct=True) for k in ["rates", "curve", "dollar", "oil", "vix"]]
        return sum(ranks) / len(ranks)
    return signal


def record(name):
    src = (HERE / "macro.py").read_text() + f"\n# signal: {name}\n"
    return src, hashlib.sha256(src.encode()).hexdigest()[:12]


def main():
    lv = macro()
    U = ev.load()
    logged = {r["hash"] for r in ev.read_log(ev.LOG)}
    for name in SIGNALS:
        src, h = record(name)
        if h in logged:
            print(f"{name}: already scored ({h})")
            continue
        cells = ev.score_cells(make(name, lv), U, "research")
        v = ev.verdict(cells, ev.n_trials(h))
        rec = dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), mode="research", kind="candidate",
                   name=f"M macro tilt: {name}", idea=f"beta to {name} (104w) x its 13w trend", hash=h, **v,
                   cells=cells, source=src)
        with open(ev.LOG, "a") as f:
            f.write(json.dumps(rec) + "\n")
        ev.show(f"M macro tilt: {name}  [{h}, research]", cells, v)


def holdout(name):
    src, h = record(name)
    if any(r["hash"] == h for r in ev.read_log(ev.HOLDOUT_LOG)):
        sys.exit("already took the holdout")
    if not any(r["hash"] == h and r["passed"] for r in ev.read_log(ev.LOG)):
        sys.exit("only a signal that passed on the research period takes the holdout")
    cells = ev.score_cells(make(name, macro()), ev.load(), "holdout")
    v = ev.verdict(cells, 1)
    with open(ev.HOLDOUT_LOG, "a") as f:
        f.write(json.dumps(dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), mode="holdout", kind="candidate",
                                name=f"M macro tilt: {name}", hash=h, **v, cells=cells, source=src)) + "\n")
    ev.show(f"M macro tilt: {name}  [{h}, HOLDOUT]", cells, v)


if __name__ == "__main__":
    holdout(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "--holdout" else main()
