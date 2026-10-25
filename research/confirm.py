"""One-shot confirmation of a logged signal on universes it has never been scored on.

  python research/confirm.py

The plan, universes and pass rules are fixed in research/prereg/CONFIRM.md and were committed
before this ran. The signal is research/prereg/confirm_combo.py, a byte-for-byte copy of the
logged candidate (hash checked). Only the research period (before 2023) is scored, with the
frozen scorecard's own cell scoring and verdict; the 2023+ holdout stays sealed. The result
goes to research/confirm_log.jsonl and the script refuses to run the same signal twice.
"""
import importlib.util, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
# research/signal.py would shadow the stdlib's signal module, which pandas imports
sys.path = [p for p in sys.path if Path(p or ".").resolve() != HERE]
import pandas as pd  # noqa: E402

spec = importlib.util.spec_from_file_location("evaluate", HERE / "evaluate.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)
bt = ev.bt

SIGNAL = HERE / "prereg" / "confirm_combo.py"
EXPECT_HASH = "e55c5c5fc3c9"      # "skewness + lottery + pullback-in-trend, equal thirds" in log.jsonl
LOG = HERE / "confirm_log.jsonl"
CACHE = ev.CACHE / "confirm_ohlcv.pkl"

# Fixed before running. Every listed fund is used if Yahoo has its history; none is added or
# dropped after seeing results.
COUNTRIES = ["EWA", "EWC", "EWD", "EWG", "EWH", "EWI", "EWJ", "EWK", "EWL", "EWN", "EWO", "EWP",
             "EWQ", "EWS", "EWU", "EWW", "EWY", "EWZ", "EWT", "EWM", "EZA", "EIS", "TUR", "THD",
             "ECH", "EPOL", "EIDO", "EPHE", "ENZL", "INDA", "MCHI", "FXI"]
STYLES = ["IVW", "IVE", "IJK", "IJJ", "IJT", "IJS", "IWF", "IWD", "IWO", "IWN", "IWP", "IWS",
          "IWM", "IWB", "IWR", "RSP", "DVY", "SPLV", "USMV", "MTUM", "QUAL", "VLUE", "SPHB",
          "PKW", "MDY", "IJH", "IJR", "OEF", "SCHD"]
UNIVERSES = [("Country ETFs vs EFA", COUNTRIES, "EFA", 10),
             ("US style ETFs vs SPY", STYLES, "SPY", 10)]


def load():
    syms = sorted({s for _, m, b, _ in UNIVERSES for s in m + [b]})
    if not CACHE.exists():
        pd.to_pickle(ev.ohlcv(syms, "max"), CACHE)
    e = {f: x[x.index >= "1999-01-01"].dropna(how="all") for f, x in pd.read_pickle(CACHE).items()}
    px = bt.weekly(e["Close"])
    bars = ev.weekly_bars(e["Close"], e["High"], e["Low"], e["Volume"], px.index)
    return [(name, px, bars, [s for s in members if s in px], bench, min_n)
            for name, members, bench, min_n in UNIVERSES]


def main():
    mod, h = ev.load_signal(SIGNAL)
    if h != EXPECT_HASH:
        sys.exit(f"{SIGNAL.name} hashes to {h}, not the logged {EXPECT_HASH}: it is not the same signal")
    if any(r["hash"] == h for r in ev.read_log(LOG)):
        sys.exit("this signal has already been confirmed on these universes; the test is one-shot")
    universes = load()
    for name, px, _, members, bench, _ in universes:
        first = px[members].apply(lambda s: s.first_valid_index())
        print(f"{name}: {len(members)} funds, benchmark {bench} from {px[bench].first_valid_index().date()}, "
              f"funds from {first.min().date()} to {first.max().date()}")
    cells = ev.score_cells(mod.signal, universes, "research")
    v = ev.verdict(cells, 1)     # one pre-registered hypothesis: the single-trial bar
    if v["passed"] and v["score"] < 0:
        v.update(passed=False, why="clears the bar in the wrong direction (the hypothesis is positive)")
    rec = dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), mode="confirm", name=mod.NAME, hash=h, **v, cells=cells)
    with open(LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")
    ev.show(f"{mod.NAME}  [{h}, confirmation on new universes, research period only]", cells, v)


if __name__ == "__main__":
    main()
