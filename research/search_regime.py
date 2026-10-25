"""Round 2 of the combination search: the same 4,525 feature sets, conditioned on market regime.

  python research/search_regime.py discover
  python research/search_regime.py validate

Rules: research/prereg/SEARCH2.md. Everything is research/search.py's machinery; only the
subsets differ. "bull" keeps the weeks when the universe's benchmark closes above its 40-week
average (about 200 days), "bear" the weeks below it, so each candidate asks whether an
effect lives in one market regime. Validation reuses 2011-2022, which round 1 already
scored 20 candidates on, so the bar counts all 40.
"""
import importlib.util, itertools, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != HERE]
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

spec = importlib.util.spec_from_file_location("search", HERE / "search.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
ev, bt = S.ev, S.bt

SUBSETS = ["bull", "bear"]
PRIOR_VALIDATED = 20      # round 1's shortlist, scored on the same validation years
OUT = S.OUT
SHORT = OUT / "shortlist_regime.json"
DISC = OUT / "discovery_regime.csv"
VAL_LOG = OUT / "validation_regime_log.jsonl"


def market(P, b):
    up = b > b.rolling(40, min_periods=30).mean()
    ok = b.rolling(40, min_periods=30).mean().notna()
    bull = pd.DataFrame(np.repeat((up & ok).to_numpy()[:, None], P.shape[1], 1), index=P.index, columns=P.columns)
    bear = pd.DataFrame(np.repeat((~up & ok).to_numpy()[:, None], P.shape[1], 1), index=P.index, columns=P.columns)
    return {"bull": bull & P.notna(), "bear": bear & P.notna()}


def make_signal(spec):
    base = S.make_signal(dict(spec, subset="all"))

    def signal(P, b, B):
        return base(P, b, B).where(market(P, b)[spec["subset"]])
    return signal


def panels():
    out = []
    for name, px, bars, members, bench, min_n in ev.load():
        P, b, B = ev.panel(px, bars, members, bench, "research")
        if P.index[0] >= S.SPLIT:
            continue
        keep = P.index < S.SPLIT
        lr = np.log(P.div(b, axis=0))
        fw = {}
        for H in S.HORIZONS:
            f = (lr.shift(-H) - lr).where(pd.Series(P.index, index=P.index).shift(-H).lt(S.SPLIT), axis=0)
            fw[H] = f[keep].rank(axis=1, pct=True).to_numpy()
        feats = {k: fn(P, b, B).reindex(index=P.index, columns=P.columns).astype(float)
                 .replace([np.inf, -np.inf], np.nan).rank(axis=1, pct=True)[keep].to_numpy() for k, fn in S.FEATURES.items()}
        m = market(P, b)
        side = {k: v[keep].to_numpy() for k, v in m.items()}
        out.append(dict(name=name, min_n=min_n, feats=feats, fwd=fw, side=side, index=P.index[keep]))
        print(f"  {name}: {keep.sum()} weeks, {side['bull'].any(1).sum()} bull / {side['bear'].any(1).sum()} bear", flush=True)
    return out


def discover():
    t0 = time.time()
    U = panels()
    sign = json.loads(S.SHORT.read_text())["signs"]   # the same directions round 1 fixed
    rows = []
    combos = [c for r in range(1, S.MAX_SIZE + 1) for c in itertools.combinations(list(S.FEATURES), r)]
    for combo in combos:
        for sub in SUBSETS:
            spec = dict(features=[(k, sign[k]) for k in combo], subset=sub)
            ts = [bt.nw_t(ic.dropna().to_numpy(), H) for H, ic in S.cand_ics(U, spec)]
            if ts:
                rows.append(dict(id=S.spec_id(spec), size=len(combo), subset=sub, score=float(np.mean(ts)),
                                 min_t=float(np.min(ts)), cells=len(ts), spec=spec))
    df = pd.DataFrame(rows).sort_values("score", ascending=False)
    df.drop(columns="spec").to_csv(DISC, index=False)
    picked, seen = [], {}
    for r in df.itertuples():
        if len(picked) >= S.SHORTLIST:
            break
        if r.cells < 4 or r.min_t <= 0:
            continue
        s = S.ic_frame(U, r.spec)
        if any(abs(s.corr(seen[p["id"]])) > S.MAX_OVERLAP for p in picked):
            continue
        seen[r.id] = s
        picked.append(dict(id=r.id, score=r.score, min_t=r.min_t, spec=r.spec))
    SHORT.write_text(json.dumps(dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), signs=sign, n_candidates=len(df),
                                     shortlist=picked), indent=1))
    print(f"\n{len(df)} candidates in {time.time() - t0:.0f}s; shortlist of {len(picked)}:")
    for p in picked:
        print(f"  {p['score']:+6.2f} (min cell t {p['min_t']:+.2f})  {p['id']}")


def validate():
    if ev.read_log(VAL_LOG):
        sys.exit("round 2 validation already ran; it is one-shot")
    sl = json.loads(SHORT.read_text())["shortlist"]
    K = PRIOR_VALIDATED + len(sl)
    U = ev.load()
    passed = 0
    for p in sl:
        fn = make_signal(p["spec"])
        cells = []
        for name, px, bars, members, bench, min_n in U:
            P, b, B = ev.panel(px, bars, members, bench, "research")
            sig = ev.check(fn, P, b, B)
            lr = np.log(P.div(b, axis=0))
            for H in S.HORIZONS:
                fwd = (lr.shift(-H) - lr)
                fwd = fwd[fwd.index >= S.SPLIT]
                sp, ic, top, bot = bt.evaluate(sig.reindex(fwd.index), fwd, H, min_n)
                sp, ic = sp.dropna(), ic.dropna()
                if len(ic) < 2 * H + 8:
                    continue
                thr = ev.placebo_t95(f"validation|{name}|{H}|{P.shape}", P[P.index >= S.SPLIT], fwd, H, min_n)
                ic_t = bt.nw_t(ic, H)
                yr = sp.groupby(sp.index.year).mean()
                net = sp.mean() - 2 * bt.COST * (bt.turnover(top, H) + bt.turnover(bot, H))
                cells.append(dict(universe=name, horizon=H, start=str(ic.index[0].date()), end=str(ic.index[-1].date()),
                                  dates=len(ic), ic=float(ic.mean()), ic_t=float(ic_t), placebo_t95=thr,
                                  ratio=float(ic_t / thr), spread=float(sp.mean()), net=float(net),
                                  yrs_pos=float((yr > 0).mean())))
        v = ev.verdict(cells, K)
        if v["passed"] and v["score"] < 0:
            v.update(passed=False, why="clears the bar in the opposite direction to discovery")
        passed += v["passed"]
        rec = dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), id=p["id"], spec=p["spec"], discovery=p["score"], **v, cells=cells)
        with open(VAL_LOG, "a") as f:
            f.write(json.dumps(rec) + "\n")
        ev.show(f"{p['id']}  [validation 2011-2022, discovery {p['score']:+.2f}]", cells, v)
    print(f"\n{passed} of {len(sl)} pass validation (bar for {K} validated candidates)")


if __name__ == "__main__":
    {"discover": discover, "validate": validate}[sys.argv[1]]()
