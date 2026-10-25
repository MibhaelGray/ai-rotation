"""The night's final exam: one consensus signal, one shot, on every universe's 2023+ data.

  python research/final.py

Rules: research/prereg/FINAL.md. The signal is search.py's construction with two features:
the equal-weight percentile rank of negative skewness (126 days) and negative 1-week relative
return, on all names. Every round on pre-2023 data converged on it. It is scored with the
frozen scorecard's holdout cells and its single-test verdict across eight universes.
"""
import importlib.util, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != HERE]


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


S = load_file("search", HERE / "search.py")
C = load_file("confirm", HERE / "confirm.py")
Bm = load_file("breadth", HERE / "breadth.py")
ev = S.ev
SPEC = dict(features=[("skew126", -1), ("rev1", -1)], subset="all")
LOG = HERE / "final_log.jsonl"


def main():
    if ev.read_log(LOG):
        sys.exit("the final exam already ran; it is one-shot")
    fn = S.make_signal(SPEC)
    U = ev.load() + C.load() + [tup for tup, _, _ in Bm.universes()]
    cells = ev.score_cells(fn, U, "holdout")
    v = ev.verdict(cells, 1)
    if v["passed"] and v["score"] < 0:
        v.update(passed=False, why="clears the bar in the wrong direction")
    with open(LOG, "a") as f:
        f.write(json.dumps(dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), mode="holdout", spec=SPEC, **v, cells=cells)) + "\n")
    ev.show("FINAL: low skewness + 1-week losers  [2023+ holdout, all universes]", cells, v)


if __name__ == "__main__":
    main()
