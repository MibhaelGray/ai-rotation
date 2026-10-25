"""One-shot test of the night's strongest AI-stock result on S&P 500 stocks.

  python research/confirm_stocks.py

Rules: research/prereg/CONFIRM_STOCKS.md. Round 2's bear-market candidate
(skewness + 1-week reversal + Amihud illiquidity, scored only in weeks the benchmark is below
its 40-week average) scored +2.84 on AI stocks at 13 weeks in validation but nothing on ETFs.
This asks whether it is a stock-level effect: does it hold on ~500 other US stocks?
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


SR = load_file("search_regime", HERE / "search_regime.py")
B = load_file("breadth", HERE / "breadth.py")
ev, bt = SR.ev, SR.bt
LOG = HERE / "confirm_log.jsonl"
TESTS = {
    "bear: skew + 1w reversal + illiquidity": dict(features=[("skew126", -1), ("rev1", -1), ("amihud", 1)], subset="bear"),
    "bear: illiquidity alone": dict(features=[("amihud", 1)], subset="bear"),
}


def universe():
    md, _, _ = B.sp500()
    stocks = [t for t in md.close.columns if t != "SPY"]
    px = bt.weekly(md.close)
    bars = ev.weekly_bars(md.close, md.high, md.low, md.volume, px.index)
    return [("S&P 500 stocks vs SPY", px, bars, stocks, "SPY", 50)]


def main():
    done = {r["name"] for r in ev.read_log(LOG)}
    U = universe()
    for name, spec in TESTS.items():
        if name in done:
            print(f"{name}: already run")
            continue
        cells = ev.score_cells(SR.make_signal(spec), U, "research")
        v = ev.verdict(cells, len(TESTS))
        if v["passed"] and v["score"] < 0:
            v.update(passed=False, why="clears the bar in the wrong direction")
        with open(LOG, "a") as f:
            f.write(json.dumps(dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), mode="confirm", name=name, spec=spec,
                                    **v, cells=cells)) + "\n")
        ev.show(f"{name}  [S&P 500 stocks, research period]", cells, v)


if __name__ == "__main__":
    main()
