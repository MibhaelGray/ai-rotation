"""Round 5: timing search. Does a combination tell when one factor will beat its benchmark?

  python research/search_ts.py discover
  python research/search_ts.py validate

Rules: research/prereg/SEARCH_TS.md. Every other test so far ranked factors against each other
each week (cross-sectional). This asks the timing question instead: for each factor, is its
indicator high or low against that factor's own history, and does that predict the factor's
own relative return over the next 4 or 13 weeks?

  z         each feature standardised per factor by its own expanding mean and standard
            deviation (at least 104 weeks), clipped at +-3; signed by discovery
  position  the mean z of 1-3 features, clipped at +-2 (long the factor against the benchmark
            when positive, short when negative)
  return    the mean over factors of position x forward relative log return, per week
  cell      Newey-West t of that weekly series; validation divides it by the 95th percentile |t|
            of 200 random-walk positions built the same way (a placebo), as the scorecard does

Discovery is 1999-2010 (outcomes before 2011) on ETFs and sectors; the 20 best distinct
combinations are validated once on 2011-2022 on all three universes. The validation bar
counts every candidate validated on those years so far (40 in rounds 1-2, plus these 20).
"""
import importlib.util, itertools, json, sys, time
from statistics import NormalDist
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != HERE]
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

spec = importlib.util.spec_from_file_location("search", HERE / "search.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
ev, bt = S.ev, S.bt

PRIOR_VALIDATED = 40
MIN_HISTORY = 104
PLACEBOS = 200
OUT = S.OUT
SHORT = OUT / "shortlist_ts.json"
DISC = OUT / "discovery_ts.csv"
VAL_LOG = OUT / "validation_ts_log.jsonl"


def zscore(f):
    """Per column: (x - expanding mean) / expanding std, using only past and current rows."""
    m = f.expanding(min_periods=MIN_HISTORY).mean()
    s = f.expanding(min_periods=MIN_HISTORY).std()
    return ((f - m) / s.replace(0, np.nan)).clip(-3, 3)


def position(zs):
    return (sum(zs) / len(zs)).clip(-2, 2)


def weekly_return(pos, fwd, min_n):
    """Mean over factors of position x forward return, on weeks with at least min_n factors."""
    x = pos * fwd
    n = x.notna().sum(axis=1)
    return x.mean(axis=1).where(n >= min_n)


def data(window):
    out = []
    for name, px, bars, members, bench, min_n in ev.load():
        P, b, B = ev.panel(px, bars, members, bench, "research")
        lr = np.log(P.div(b, axis=0))
        z = {k: zscore(fn(P, b, B).reindex(index=P.index, columns=P.columns).astype(float)
                       .replace([np.inf, -np.inf], np.nan)) for k, fn in S.FEATURES.items()}
        fw = {H: lr.shift(-H) - lr for H in S.HORIZONS}
        if window == "discovery":
            if P.index[0] >= S.SPLIT:
                continue
            ok = pd.Series(P.index, index=P.index)
            for H in S.HORIZONS:
                fw[H] = fw[H].where(ok.shift(-H).lt(S.SPLIT), axis=0)
        else:
            for H in S.HORIZONS:
                fw[H] = fw[H][fw[H].index >= S.SPLIT]
        out.append(dict(name=name, min_n=min_n, z=z, fwd=fw, P=P))
        print(f"  {name}: {P.shape[1]} factors", flush=True)
    return out


def cells(U, spec):
    res = []
    for u in U:
        pos = position([u["z"][k] * sg for k, sg in spec["features"]])
        for H in S.HORIZONS:
            r = weekly_return(pos.reindex(u["fwd"][H].index), u["fwd"][H], u["min_n"]).dropna()
            if len(r) >= 2 * H + 8:
                res.append((u, H, r))
    return res


def discover():
    t0 = time.time()
    U = data("discovery")
    sign = {}
    for k in S.FEATURES:
        ts = [bt.nw_t(r, H) for _, H, r in cells(U, dict(features=[(k, 1)]))]
        sign[k] = 1 if np.nanmean(ts) >= 0 else -1
    rows = []
    for combo in (c for n in range(1, S.MAX_SIZE + 1) for c in itertools.combinations(list(S.FEATURES), n)):
        spec = dict(features=[(k, sign[k]) for k in combo], subset="all")
        ts = [bt.nw_t(r, H) for _, H, r in cells(U, spec)]
        if ts:
            rows.append(dict(id="ts:" + "+".join(f"{'' if s > 0 else '-'}{k}" for k, s in spec["features"]),
                             score=float(np.mean(ts)), min_t=float(np.min(ts)), cells=len(ts), spec=spec))
    df = pd.DataFrame(rows).sort_values("score", ascending=False)
    df.drop(columns="spec").to_csv(DISC, index=False)
    picked, seen = [], {}
    for r in df.itertuples():
        if len(picked) >= S.SHORTLIST:
            break
        if r.cells < 4 or r.min_t <= 0:
            continue
        s = pd.concat([x for _, _, x in cells(U, r.spec)])
        if any(abs(s.corr(seen[p["id"]])) > S.MAX_OVERLAP for p in picked):
            continue
        seen[r.id] = s
        picked.append(dict(id=r.id, score=r.score, min_t=r.min_t, spec=r.spec))
    SHORT.write_text(json.dumps(dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), signs=sign, n_candidates=len(df),
                                     shortlist=picked), indent=1))
    print(f"\n{len(df)} candidates in {time.time() - t0:.0f}s; shortlist of {len(picked)}:")
    for p in picked:
        print(f"  {p['score']:+6.2f} (min cell t {p['min_t']:+.2f})  {p['id']}")


def placebo_t95(u, H, rng):
    P = u["P"]
    ts = []
    for _ in range(PLACEBOS):
        w = pd.DataFrame(rng.standard_normal(P.shape).cumsum(axis=0), index=P.index, columns=P.columns).where(P.notna())
        pos = position([zscore(w)])
        r = weekly_return(pos.reindex(u["fwd"][H].index), u["fwd"][H], u["min_n"]).dropna()
        ts.append(abs(bt.nw_t(r, H)))
    return float(np.nanpercentile(ts, 95))


def validate():
    if ev.read_log(VAL_LOG):
        sys.exit("round 5 validation already ran; it is one-shot")
    sl = json.loads(SHORT.read_text())["shortlist"]
    K = PRIOR_VALIDATED + len(sl)
    U = data("validation")
    rng = np.random.default_rng(5)
    thr = {(u["name"], H): placebo_t95(u, H, rng) for u in U for H in S.HORIZONS}
    print("placebo t95:", {f"{k[0].split()[0]}{k[1]}": round(v, 2) for k, v in thr.items()}, flush=True)
    bar = NormalDist().inv_cdf(1 - 0.05 / (2 * K)) / NormalDist().inv_cdf(0.975)
    n_pass = 0
    for p in sl:
        cs = []
        for u, H, r in cells(U, p["spec"]):
            t = bt.nw_t(r, H)
            yr = r.groupby(r.index.year).mean()
            cs.append(dict(universe=u["name"], horizon=H, weeks=len(r), mean=float(r.mean()), t=float(t),
                           placebo_t95=thr[(u["name"], H)], ratio=float(t / thr[(u["name"], H)]),
                           yrs_pos=float((yr > 0).mean())))
        score = float(np.mean([c["ratio"] for c in cs]))
        why = []
        if score < bar:
            why.append(f"score {score:+.2f} < bar {bar:.2f}")
        if any(c["ratio"] <= 0 for c in cs):
            why.append("negative in some cell")
        if np.mean([c["yrs_pos"] for c in cs]) < ev.MIN_YEARS_POSITIVE:
            why.append("positive in < 60% of years")
        passed = not why
        n_pass += passed
        rec = dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), id=p["id"], spec=p["spec"], discovery=p["score"],
                   score=score, bar=bar, passed=passed, why="; ".join(why) or "clears every test", cells=cs)
        with open(VAL_LOG, "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"{score:+5.2f} {'PASS' if passed else 'fail'}  " +
              " ".join(f"{c['universe'].split()[0][:3]}{c['horizon']}={c['ratio']:+.2f}" for c in cs) + f"  {p['id']}", flush=True)
    print(f"\n{n_pass} of {len(sl)} pass validation (bar {bar:.2f} for {K} validated candidates)")


if __name__ == "__main__":
    {"discover": discover, "validate": validate}[sys.argv[1]]()
