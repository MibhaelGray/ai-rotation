"""Round 9: the combination search on baskets built from their members. Rules: research/prereg/SEARCH_BASKETS.md.

  python research/search_baskets.py discover
  python research/search_baskets.py validate

The same method as search.py (1-3 features, equal-weight percentile ranks, all / right / left
of the RRG centre, directions fixed by discovery), on factor-like baskets instead of ETFs:
  discovery   S&P sub-industry and sector baskets, 1999-2010 (outcomes before 2011)
  validation  the same baskets plus the AI layers, 2011-2022, once
Features: search.py's 30 plus the 4 breadth measures from breadth.py, which need members.
"""
import importlib.util, itertools, json, sys, time
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
Bm = load_file("breadth", HERE / "breadth.py")
ev, bt = S.ev, S.bt

PRIOR_ON_THESE = 4           # breadth.py's four signals were scored on these baskets' 2011-2022
OUT = S.OUT
SHORT = OUT / "shortlist_baskets.json"
DISC = OUT / "discovery_baskets.csv"
VAL_LOG = OUT / "validation_baskets_log.jsonl"


def features(md, members):
    f = dict(S.FEATURES)
    for k in Bm.SIGNALS:
        f["br_" + k] = (lambda k: lambda P, b, B: Bm.make(k, md, members)(P, b, B))(k)
    return f


def make_signal(spec, feats):
    def signal(P, b, B):
        rsr = S._rrg(P, b)[0]
        keep = {"all": P.notna(), "right": rsr >= 100, "left": rsr < 100}[spec["subset"]]
        ranks = []
        for name, sign in spec["features"]:
            x = feats[name](P, b, B).reindex(index=P.index, columns=P.columns).astype(float).replace([np.inf, -np.inf], np.nan)
            ranks.append(x.rank(axis=1, pct=True) if sign > 0 else 1 - x.rank(axis=1, pct=True))
        return (sum(ranks) / len(ranks)).where(keep & rsr.notna())
    return signal


def panels():
    out = []
    for (name, px, bars, members, bench, min_n), md, mem in Bm.universes():
        P, b, B = ev.panel(px, bars, members, bench, "research")
        if P.index[0] >= S.SPLIT:
            continue
        keep = P.index < S.SPLIT
        lr = np.log(P.div(b, axis=0))
        fw = {}
        for H in S.HORIZONS:
            f = (lr.shift(-H) - lr).where(pd.Series(P.index, index=P.index).shift(-H).lt(S.SPLIT), axis=0)
            fw[H] = f[keep].rank(axis=1, pct=True).to_numpy()
        rsr = S._rrg(P, b)[0]
        feats = {k: fn(P, b, B).reindex(index=P.index, columns=P.columns).astype(float).replace([np.inf, -np.inf], np.nan)
                 .rank(axis=1, pct=True)[keep].to_numpy() for k, fn in features(md, mem).items()}
        side = {"all": P.notna()[keep].to_numpy(), "right": (rsr >= 100)[keep].to_numpy(), "left": (rsr < 100)[keep].to_numpy()}
        out.append(dict(name=name, min_n=min_n, feats=feats, fwd=fw, side=side, index=P.index[keep]))
        print(f"  {name}: {keep.sum()} weeks x {P.shape[1]} baskets", flush=True)
    return out


def discover():
    t0 = time.time()
    U = panels()
    names = list(U[0]["feats"])
    sign = {}
    for k in names:
        ics = [np.nanmean(S.masked_corr(u["feats"][k], u["fwd"][H], u["min_n"])) for u in U for H in S.HORIZONS]
        sign[k] = 1 if np.nanmean(ics) >= 0 else -1
    rows = []
    combos = [c for r in range(1, S.MAX_SIZE + 1) for c in itertools.combinations(names, r)]
    print(f"{len(combos)} feature sets x {len(S.SUBSETS)} subsets", flush=True)
    for combo in combos:
        for sub in S.SUBSETS:
            spec = dict(features=[(k, sign[k]) for k in combo], subset=sub)
            ts = [bt.nw_t(ic.dropna().to_numpy(), H) for H, ic in S.cand_ics(U, spec)]
            if ts:
                rows.append(dict(id=S.spec_id(spec), score=float(np.mean(ts)), min_t=float(np.min(ts)), cells=len(ts), spec=spec))
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
        sys.exit("round 9 validation already ran; it is one-shot")
    sl = json.loads(SHORT.read_text())["shortlist"]
    K = PRIOR_ON_THESE + len(sl)
    U = Bm.universes()
    n_pass = 0
    for p in sl:
        cells = []
        for (name, px, bars, members, bench, min_n), md, mem in U:
            fn = make_signal(p["spec"], features(md, mem))
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
                cells.append(dict(universe=name, horizon=H, dates=len(ic), ic=float(ic.mean()), ic_t=float(ic_t),
                                  placebo_t95=thr, ratio=float(ic_t / thr), spread=float(sp.mean()), net=float(net),
                                  yrs_pos=float((yr > 0).mean())))
        v = ev.verdict(cells, K)
        if v["passed"] and v["score"] < 0:
            v.update(passed=False, why="clears the bar in the opposite direction to discovery")
        n_pass += v["passed"]
        with open(VAL_LOG, "a") as f:
            f.write(json.dumps(dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), id=p["id"], spec=p["spec"],
                                    discovery=p["score"], **v, cells=cells)) + "\n")
        print(f"{v['score']:+5.2f} {'PASS' if v['passed'] else 'fail'}  " +
              " ".join(f"{c['universe'].split()[1][:4]}{c['horizon']}={c['ratio']:+.2f}" for c in cells) + f"  {p['id']}", flush=True)
    print(f"\n{n_pass} of {len(sl)} pass validation (bar for {K} tests on these baskets' 2011-2022)")


if __name__ == "__main__":
    {"discover": discover, "validate": validate}[sys.argv[1]]()
