"""One-shot confirmation of the logged skewness signal on the country and style ETFs.

  python research/confirm_skew.py

Rules: research/prereg/CONFIRM_SKEW.md. It uses confirm.py's universes and data unchanged.
These universes were used once before, for the equal-thirds combo, so the bar counts 2 tests.
"""
import importlib.util, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != HERE]

spec = importlib.util.spec_from_file_location("confirm", HERE / "confirm.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
ev = C.ev

SIGNAL = HERE / "prereg" / "confirm_skew.py"
EXPECT_HASH = "fe7bfe1142bc"      # "negative skewness of relative returns 126d" in log.jsonl
TESTS_ON_THESE_UNIVERSES = 2


def main():
    mod, h = ev.load_signal(SIGNAL)
    if h != EXPECT_HASH:
        sys.exit(f"{SIGNAL.name} hashes to {h}, not the logged {EXPECT_HASH}")
    if any(r["hash"] == h for r in ev.read_log(C.LOG)):
        sys.exit("already confirmed on these universes; one-shot")
    cells = ev.score_cells(mod.signal, C.load(), "research")
    v = ev.verdict(cells, TESTS_ON_THESE_UNIVERSES)
    if v["passed"] and v["score"] < 0:
        v.update(passed=False, why="clears the bar in the wrong direction")
    with open(C.LOG, "a") as f:
        f.write(json.dumps(dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), mode="confirm", name=mod.NAME, hash=h,
                                **v, cells=cells)) + "\n")
    ev.show(f"{mod.NAME}  [{h}, confirmation on country and style ETFs]", cells, v)


if __name__ == "__main__":
    main()
