"""Combination search with a discovery/validation split. Rules: research/prereg/SEARCH.md.

  python research/search.py discover     screen every combination on 1999-2010, write the shortlist
  python research/search.py validate     score the shortlist once on 2011-2022, all universes

A blind search over thousands of combinations will always turn up something that looks good
on the data it was picked from. So the research period is split in two:

  discovery   signal dates before 2011, with outcomes also before 2011. ETFs and sectors only
              (the AI stocks have no history then). Every combination is screened here.
  validation  signal dates from 2011 to the end of 2022, on all three universes. Only the
              shortlist is scored, once, with the frozen scorecard's own placebo-calibrated cells
              and a bar Bonferroni-adjusted for the shortlist size.

Nothing here touches 2023 onward. A validated finalist goes to evaluate.py's one-shot holdout.

A combination is the equal-weight mean of 1-3 features' cross-sectional percentile ranks,
each feature's direction fixed by its own discovery IC, optionally restricted to the names
right or left of centre on the weekly RRG.
"""
import hashlib, importlib.util, itertools, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path = [p for p in sys.path if Path(p or ".").resolve() != HERE]
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

spec = importlib.util.spec_from_file_location("evaluate", HERE / "evaluate.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)
bt = ev.bt

SPLIT = pd.Timestamp("2011-01-01")
HORIZONS = ev.HORIZONS
MAX_SIZE = 3
SHORTLIST = 20
MAX_OVERLAP = 0.9          # skip a combination whose discovery IC series correlates above this with a picked one
SUBSETS = ["all", "right", "left"]
OUT = HERE / "search"
SHORT = OUT / "shortlist.json"
DISC = OUT / "discovery.csv"
VAL_LOG = OUT / "validation_log.jsonl"


# ---------------------------------------------------------------- features
# Each takes (P, b, B): weekly closes, the benchmark, and Bars with daily data; returns a
# weekly frame shaped like P. Direction is not assumed; discovery fixes it.

def _rel(P, b, B):
    d = B.daily.close
    return np.log(d[P.columns].div(d[b.name], axis=0)).diff()


def _wk(f, P):
    return f.reindex(P.index, method="ffill").where(P.notna())


def _hlc(P, B):
    d = B.daily
    return d.close[P.columns], d.high[P.columns], d.low[P.columns]


def _atr(c, h, l, n):
    pc = c.shift(1)
    tr = np.maximum(h - l, np.maximum((h - pc).abs(), (l - pc).abs())).where(c.notna())
    return tr.rolling(n, min_periods=int(n * 0.75)).mean()


def _rrg(P, b):
    sm = (100 * P.div(b, axis=0)).ewm(span=3, adjust=False).mean()
    rsr = 100 * sm / sm.rolling(10).mean()
    rsm = (100 * rsr / rsr.shift(1)).ewm(span=3, adjust=False).mean()
    return rsr, rsm


def _rs(P, b):
    return P.div(b, axis=0)


FEATURES = {
    "lottery21": lambda P, b, B: _wk(_rel(P, b, B).rolling(21, min_periods=15).max(), P),
    "crash21": lambda P, b, B: _wk(_rel(P, b, B).rolling(21, min_periods=15).min(), P),
    "skew126": lambda P, b, B: _wk(_rel(P, b, B).rolling(126, min_periods=90).skew(), P),
    "vol63": lambda P, b, B: _wk(_rel(P, b, B).rolling(63, min_periods=45).std(), P),
    "vol_ratio": lambda P, b, B: _wk(np.log(_rel(P, b, B).rolling(20, min_periods=15).std()
                                            / _rel(P, b, B).rolling(120, min_periods=90).std()), P),
    "continuity126": lambda P, b, B: _wk(np.sign(_rel(P, b, B)).rolling(126, min_periods=90).mean(), P),
    "efficiency63": lambda P, b, B: _wk(_rel(P, b, B).rolling(63, min_periods=45).sum()
                                        / _rel(P, b, B).abs().rolling(63, min_periods=45).sum(), P),
    "beta63": lambda P, b, B: _wk(_beta(P, b, B), P),
    "rsi14": lambda P, b, B: _wk(_rsi(_rel(P, b, B)), P),
    "mom26s4": lambda P, b, B: np.log(_rs(P, b).shift(4) / _rs(P, b).shift(26))
                               / np.log(_rs(P, b)).diff().rolling(26, min_periods=20).std(),
    "mom12": lambda P, b, B: np.log(_rs(P, b) / _rs(P, b).shift(12)),
    "mom52s4": lambda P, b, B: np.log(_rs(P, b).shift(4) / _rs(P, b).shift(52)),
    "rev4": lambda P, b, B: np.log(_rs(P, b) / _rs(P, b).shift(4)),
    "rev1": lambda P, b, B: np.log(_rs(P, b) / _rs(P, b).shift(1)),
    "high52": lambda P, b, B: np.log(_rs(P, b) / _rs(P, b).rolling(52, min_periods=40).max()),
    "trend40": lambda P, b, B: np.log(_rs(P, b) / _rs(P, b).rolling(40, min_periods=30).mean()),
    "rs_ratio": lambda P, b, B: _rrg(P, b)[0],
    "rs_mom": lambda P, b, B: _rrg(P, b)[1],
    "rrg_dist": lambda P, b, B: np.hypot(_rrg(P, b)[0] - 100, _rrg(P, b)[1] - 100),
    "rsr_z52": lambda P, b, B: (_rrg(P, b)[0] - _rrg(P, b)[0].rolling(52, min_periods=26).mean())
                               / _rrg(P, b)[0].rolling(52, min_periods=26).std(),
    "tenure": lambda P, b, B: _tenure(P, b),
    "price_trend200": lambda P, b, B: _wk(np.log(_hlc(P, B)[0] / _hlc(P, B)[0].rolling(200, min_periods=150).mean()), P),
    "atr_stretch": lambda P, b, B: _wk(_atr_stretch(P, B), P),
    "range_exp": lambda P, b, B: _wk(_range_exp(P, B), P),
    "close_loc10": lambda P, b, B: _wk(_close_loc(P, B), P),
    "squeeze": lambda P, b, B: _wk(_squeeze(P, B), P),
    "abn_volume": lambda P, b, B: _wk(_abn_vol(P, B), P),
    "accumulation": lambda P, b, B: _wk(_accum(P, b, B), P),
    "capitulation": lambda P, b, B: _wk(_capit(P, b, B), P),
    "amihud": lambda P, b, B: _wk(_amihud(P, B), P),
}


def _beta(P, b, B):
    d = B.daily.close
    r = np.log(d[P.columns]).diff()
    m = np.log(d[b.name]).diff()
    cov = r.rolling(63, min_periods=45).cov(m)
    return cov.div(m.rolling(63, min_periods=45).var(), axis=0)


def _rsi(r):
    up = r.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-r.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def _tenure(P, b):
    rsr, rsm = _rrg(P, b)
    q = (rsr >= 100).astype(int) * 2 + (rsm >= 100).astype(int)
    q = q.where(rsr.notna() & rsm.notna())
    run = q.ne(q.shift()).cumsum()
    return np.log(pd.DataFrame({c: q[c].groupby(run[c]).cumcount() + 1 for c in q}).where(q.notna()))


def _atr_stretch(P, B):
    c, h, l = _hlc(P, B)
    return (c - c.rolling(50, min_periods=40).mean()) / _atr(c, h, l, 14)


def _range_exp(P, B):
    c, h, l = _hlc(P, B)
    return np.log(_atr(c, h, l, 10) / _atr(c, h, l, 60))


def _close_loc(P, B):
    c, h, l = _hlc(P, B)
    return ((c - l) / (h - l).replace(0, np.nan)).rolling(10, min_periods=7).mean()


def _squeeze(P, B):
    c, h, l = _hlc(P, B)
    rng = h.rolling(20, min_periods=15).max() - l.rolling(20, min_periods=15).min()
    return np.log(rng / _atr(c, h, l, 20))


def _vol(P, B):
    return B.daily.volume[P.columns].replace(0, np.nan)


def _abn_vol(P, B):
    v = _vol(P, B)
    return np.log(v.rolling(20, min_periods=15).mean() / v.rolling(250, min_periods=180).mean())


def _accum(P, b, B):
    r, v = _rel(P, b, B), _vol(P, B)
    up = v.where(r > 0, 0).rolling(50, min_periods=40).sum()
    dn = v.where(r < 0, 0).rolling(50, min_periods=40).sum()
    return np.log((up + 1) / (dn + 1)).where(r.notna() & v.notna())


def _capit(P, b, B):
    c, h, l = _hlc(P, B)
    d = B.daily.close
    rs = d[P.columns].div(d[b.name], axis=0)
    return -np.log(rs / rs.shift(20)) * (_atr(c, h, l, 10) / _atr(c, h, l, 60))


def _amihud(P, B):
    c = _hlc(P, B)[0]
    dv = _vol(P, B) * c
    return np.log((np.log(c).diff().abs() / dv).rolling(63, min_periods=45).mean())


# ---------------------------------------------------------------- the exact signal for a spec

def make_signal(spec):
    """spec = dict(features=[(name, sign)], subset=...). Returns signal(P, b, B) as scored."""
    def signal(P, b, B):
        rsr = _rrg(P, b)[0]
        keep = {"all": P.notna(), "right": rsr >= 100, "left": rsr < 100}[spec["subset"]]
        ranks = []
        for name, sign in spec["features"]:
            f = FEATURES[name](P, b, B).reindex(index=P.index, columns=P.columns).astype(float)
            f = f.replace([np.inf, -np.inf], np.nan)
            ranks.append(f.rank(axis=1, pct=True) if sign > 0 else 1 - f.rank(axis=1, pct=True))
        s = sum(ranks) / len(ranks)
        return s.where(keep & rsr.notna())
    return signal


def spec_id(spec):
    return f"{spec['subset']}:" + "+".join(f"{'' if s > 0 else '-'}{n}" for n, s in spec["features"])


# ---------------------------------------------------------------- discovery

def masked_corr(S, F, min_n):
    """Per-row Pearson correlation of S and F over rows' common non-NaN entries."""
    m = ~np.isnan(S) & ~np.isnan(F)
    n = m.sum(1)
    S0, F0 = np.where(m, S, 0.0), np.where(m, F, 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        ms, mf = S0.sum(1) / n, F0.sum(1) / n
        Sc, Fc = np.where(m, S0 - ms[:, None], 0), np.where(m, F0 - mf[:, None], 0)
        c = (Sc * Fc).sum(1) / np.sqrt((Sc ** 2).sum(1) * (Fc ** 2).sum(1))
    c[n < min_n] = np.nan
    return c


def panels(window):
    """Per research universe: ranked features, RRG side masks and ranked forward returns.

    window "discovery": signal dates before SPLIT with outcomes before SPLIT, ETFs and sectors.
    """
    out = []
    for name, px, bars, members, bench, min_n in ev.load():
        P, b, B = ev.panel(px, bars, members, bench, "research")
        if window == "discovery":
            if P.index[0] >= SPLIT:
                continue
            keep_rows = P.index < SPLIT
        lr = np.log(P.div(b, axis=0))
        fw = {}
        for H in HORIZONS:
            f = lr.shift(-H) - lr
            if window == "discovery":
                f = f.where(pd.Series(P.index, index=P.index).shift(-H).lt(SPLIT), axis=0)
                f = f[keep_rows]
            fw[H] = f.rank(axis=1, pct=True).to_numpy()
        rsr = _rrg(P, b)[0]
        feats = {}
        for k, fn in FEATURES.items():
            f = fn(P, b, B).reindex(index=P.index, columns=P.columns).astype(float).replace([np.inf, -np.inf], np.nan)
            feats[k] = f.rank(axis=1, pct=True)[keep_rows].to_numpy()
        side = {"all": P.notna()[keep_rows].to_numpy(), "right": (rsr >= 100)[keep_rows].to_numpy(),
                "left": (rsr < 100)[keep_rows].to_numpy()}
        out.append(dict(name=name, min_n=min_n, feats=feats, fwd=fw, side=side, index=P.index[keep_rows]))
        print(f"  {name}: {len(P.index[keep_rows])} weeks x {P.shape[1]} names", flush=True)
    return out


def cand_ics(U, spec):
    """(horizon, weekly IC series) for every discovery cell with enough weeks."""
    out = []
    for u in U:
        S = np.mean([u["feats"][k] if sg > 0 else 1 - u["feats"][k] for k, sg in spec["features"]], axis=0)
        S = np.where(u["side"][spec["subset"]], S, np.nan)
        for H in HORIZONS:
            ic = pd.Series(masked_corr(S, u["fwd"][H], u["min_n"]), index=u["index"]).rename(f"{u['name']}|{H}")
            if ic.notna().sum() >= 2 * H + 8:
                out.append((H, ic))
    return out


def ic_frame(U, spec):
    return pd.concat([ic for _, ic in cand_ics(U, spec)], axis=1).stack()


def discover():
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    print("building discovery panels (before 2011)", flush=True)
    U = panels("discovery")
    names = list(FEATURES)
    # each feature's direction: the sign of its mean discovery IC over every cell
    sign = {}
    for k in names:
        ics = [np.nanmean(masked_corr(u["feats"][k], u["fwd"][H], u["min_n"])) for u in U for H in HORIZONS]
        sign[k] = 1 if np.nanmean(ics) >= 0 else -1
    rows = []
    combos = [c for r in range(1, MAX_SIZE + 1) for c in itertools.combinations(names, r)]
    print(f"{len(combos)} feature sets x {len(SUBSETS)} subsets = {len(combos) * len(SUBSETS)} candidates", flush=True)
    for i, combo in enumerate(combos):
        for sub in SUBSETS:
            spec = dict(features=[(k, sign[k]) for k in combo], subset=sub)
            ts = [bt.nw_t(ic.dropna().to_numpy(), H) for H, ic in cand_ics(U, spec)]
            if not ts:
                continue
            rows.append(dict(id=spec_id(spec), size=len(combo), subset=sub, score=float(np.mean(ts)),
                             min_t=float(np.min(ts)), cells=len(ts), spec=spec))
        if i % 500 == 0:
            print(f"  {i}/{len(combos)} feature sets, {time.time() - t0:.0f}s", flush=True)
    df = pd.DataFrame(rows).sort_values("score", ascending=False)
    df.drop(columns="spec").to_csv(DISC, index=False)
    # shortlist: best discovery scores, skipping near-duplicates of what is already picked
    picked, seen = [], {}
    for r in df.itertuples():
        if len(picked) >= SHORTLIST:
            break
        if r.cells < 4 or r.min_t <= 0:
            continue
        s = ic_frame(U, r.spec)
        if any(abs(s.corr(seen[p["id"]])) > MAX_OVERLAP for p in picked):
            continue
        seen[r.id] = s
        picked.append(dict(id=r.id, score=r.score, min_t=r.min_t, spec=r.spec))
    SHORT.write_text(json.dumps(dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), signs=sign, n_candidates=len(df),
                                     shortlist=picked), indent=1))
    print(f"\n{len(df)} candidates screened in {time.time() - t0:.0f}s; shortlist of {len(picked)}:")
    for p in picked:
        print(f"  {p['score']:+6.2f} (min cell t {p['min_t']:+.2f})  {p['id']}")


# ---------------------------------------------------------------- validation

def validate():
    sl = json.loads(SHORT.read_text())
    done = {r["id"] for r in ev.read_log(VAL_LOG)}
    if done:
        sys.exit(f"validation already ran for {len(done)} candidates; it is one-shot")
    K = len(sl["shortlist"])
    U = ev.load()
    results = []
    for p in sl["shortlist"]:
        fn = make_signal(p["spec"])
        cells = []
        for name, px, bars, members, bench, min_n in U:
            P, b, B = ev.panel(px, bars, members, bench, "research")
            sig = ev.check(fn, P, b, B)
            lr = np.log(P.div(b, axis=0))
            for H in HORIZONS:
                fwd = (lr.shift(-H) - lr)
                fwd = fwd[fwd.index >= SPLIT]
                sp, ic, top, bot = bt.evaluate(sig.reindex(fwd.index), fwd, H, min_n)
                sp, ic = sp.dropna(), ic.dropna()
                if len(ic) < 2 * H + 8:
                    continue
                thr = ev.placebo_t95(f"validation|{name}|{H}|{P.shape}", P[P.index >= SPLIT], fwd, H, min_n)
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
        rec = dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), id=p["id"], spec=p["spec"], discovery=p["score"], **v, cells=cells)
        with open(VAL_LOG, "a") as f:
            f.write(json.dumps(rec) + "\n")
        ev.show(f"{p['id']}  [validation 2011-2022, discovery {p['score']:+.2f}]", cells, v)
        results.append(rec)
    print(f"\n{sum(r['passed'] for r in results)} of {K} pass validation (bar {results[0]['bar']:.2f} for {K} candidates)")


if __name__ == "__main__":
    {"discover": discover, "validate": validate}[sys.argv[1]]()
