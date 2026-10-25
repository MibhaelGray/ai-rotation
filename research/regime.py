"""The regime scorecard: do indicators forecast which RRG quadrant a factor rotates into?

  python research/regime.py --baseline          how well the RRG alone forecasts, writes regime_baseline.md
  python research/regime.py --list              the indicators in research/regime_indicators.py
  python research/regime.py tenure              score one indicator on the research period
  python research/regime.py tenure skew         score a combination (all features in one model)
  python research/regime.py --singles           score every indicator alone
  python research/regime.py --placebo 20        random-walk indicators, not logged: is the test calibrated?
  python research/regime.py --holdout --confirm a b   the one-shot final exam on 2023 onward
  --scratch    score without logging (plumbing tests only)

Each week, for each factor, the page's weekly RRG (RS-Ratio and RS-Momentum against the
benchmark, EMA 3, 10-week base, 1-bar momentum) puts it in one of four quadrants. The
question is which quadrant it will be in H weeks later (H = 4 and 13).

The baseline already knows a lot: quadrants persist and rotate clockwise, and position and
speed on the chart say where a dot is heading. It is a multinomial logistic model of the
future quadrant on the current quadrant, RS-Ratio and RS-Momentum (each per quadrant) and
their one-week changes. A candidate adds its indicators, each interacted with the current
quadrant so it can matter differently in Leading than in Lagging. Both models are refitted
walk-forward every 13 weeks on rows whose outcome was known at the time, and judged only on
the weeks after each fit.

Per (universe, horizon) cell:
  skill    out-of-sample log-loss of the baseline minus the candidate's, averaged per week
           (positive = the indicator improves the forecast), Newey-West t with H lags
  payoff   rank IC between the candidate's change to P(right of centre in H weeks) and the
           forward relative return over H weeks: do the forecast changes point the way prices go?
  years    share of calendar years with positive skill

Score = mean skill t over the cells the indicator is defined in (it must be defined in at
least two universes). The bar is the one-sided Bonferroni z for 5% over every distinct
candidate in regime_log.jsonl, so it rises as more are tried.
FORECASTS: score at or above the bar, skill t positive in every cell, positive in >= 60% of years.
PAYS:      payoff IC positive in every cell.
PASS needs both.

Research mode cuts all data before HOLDOUT_START before anything is computed. Holdout mode
fits on everything known at each date and scores only weeks from HOLDOUT_START, once per
candidate, after a research-period score.
"""
import argparse, hashlib, importlib.util, inspect, json, sys, time
from statistics import NormalDist
from pathlib import Path
# Run as a script, research/ is first on the path and research/signal.py would shadow the
# stdlib's signal module, which pandas imports.
sys.path = [p for p in sys.path if Path(p or ".").resolve() != Path(__file__).resolve().parent]
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))
import backtest as bt  # noqa: E402


def load_file(name, path):
    """Import a module from research/ by path: research/signal.py would shadow the stdlib's signal."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ev = load_file("evaluate", HERE / "evaluate.py")

HOLDOUT_START = ev.HOLDOUT_START
HORIZONS = [4, 13]
REFIT = 13                 # weeks between walk-forward refits
MIN_TRAIN = 104            # labelled weeks before the first out-of-sample forecast
MIN_YEARS_POSITIVE = 0.6
RIDGE = 1.0
LOG = HERE / "regime_log.jsonl"
HOLDOUT_LOG = HERE / "regime_holdout_log.jsonl"
QUADS = ["Leading", "Weakening", "Lagging", "Improving"]   # clockwise; codes 0..3


# ---------------------------------------------------------------- universes

def ema(f, span):
    return f.ewm(span=span, adjust=False).mean()


def rrg(px, b):
    """The page's weekly RRG: RS-Ratio, RS-Momentum and quadrant code (0 L, 1 W, 2 Lagging, 3 I)."""
    sm = ema(100 * px.div(b, axis=0), 3)
    rsr = 100 * sm / sm.rolling(10).mean()
    rsm = ema(100 * rsr / rsr.shift(1), 3)
    q = np.where(rsr >= 100, np.where(rsm >= 100, 0, 1), np.where(rsm >= 100, 3, 2)).astype(float)
    q = pd.DataFrame(q, index=px.index, columns=px.columns).where(rsr.notna() & rsm.notna())
    return rsr, rsm, q


def weekly_last(f, end):
    """Friday closes up to end; a week that has not finished by end is dropped."""
    w = f.loc[:end].resample("W-FRI").last()
    return w[w.index <= min(end, f.index[-1])]


class Universe:
    """One universe cut at `end`. What an indicator may use:

    px, b        weekly closes of the factors and of the benchmark (named bench)
    d            daily Bars of the factors plus the benchmark column: close, high, low, volume
                 (a basket's high/low is its index times its members' mean high/close and low/close,
                 its volume is members' summed dollar volume)
    rsr, rsm, q  the weekly RRG and quadrant code of each factor (0 Leading, 1 Weakening,
                 2 Lagging, 3 Improving)
    members      factor -> list of member tickers, or None when the factors have no members
    md           daily Bars of the member stocks plus the benchmark (None without members)
    weekly(f)    a daily frame sampled on the weekly rows
    """
    def __init__(self, name, bench, d, members, md, end):
        self.name, self.bench, self.members, self.md, self.end = name, bench, members, md, end
        self.d = d
        self.px = weekly_last(d.close.drop(columns=bench), end).dropna(axis=1, how="all")
        self.b = weekly_last(d.close[bench], end).reindex(self.px.index)
        self.px = self.px[self.b.notna()]
        self.b = self.b[self.b.notna()]
        self.rsr, self.rsm, self.q = rrg(self.px, self.b)

    def weekly(self, f):
        return f.reindex(self.px.index, method="ffill").reindex(columns=self.px.columns)


def cut(bars, cols, end):
    f = lambda x: x.loc[:end, [c for c in cols if c in x]]
    return ev.Bars(f(bars.close), f(bars.high), f(bars.low), f(bars.volume))


def baskets(d, groups, level):
    """factor -> member tickers for the AI layers or subsectors, as the page groups them."""
    out = {}
    for tier, layers in groups.items():
        for layer, node in layers.items():
            if level == "layer":
                out[layer] = sorted(set(bt.tickers(node)) & set(d.close))
            elif isinstance(node, dict) and "_tickers" not in node:
                for sub, leaf in node.items():
                    out[f"{layer} / {sub}"] = sorted(set(bt.tickers(leaf)) & set(d.close))
            else:
                out[layer] = sorted(set(bt.tickers(node)) & set(d.close))
    return {k: v for k, v in out.items() if len(v) >= 2}


def basket_bars(md, members, min_members=2):
    """Equal-weight daily index per basket, rebalanced daily, as the page builds it."""
    close = md.close.ffill(limit=5)
    ret = close.pct_change(fill_method=None)
    hr, lr = (md.high / md.close).clip(lower=1), (md.low / md.close).clip(upper=1)
    dv = md.volume * md.close
    C, H, L, V = {}, {}, {}, {}
    for k, m in members.items():
        r = ret[m]
        ok = r.notna().sum(axis=1) >= min_members
        idx = (1 + r.mean(axis=1).where(ok, 0)).cumprod().where(ok.cummax())
        idx = idx.where(close[m].notna().sum(axis=1) >= min_members)
        C[k], H[k], L[k] = idx, idx * hr[m].mean(axis=1), idx * lr[m].mean(axis=1)
        V[k] = dv[m].sum(axis=1, min_count=min_members)
    F = lambda x: pd.DataFrame(x)
    return F(C), F(H), F(L), F(V)


_RAW = {}


def raw():
    """Daily bars for the ETFs and for the AI stocks, plus the AI basket groups."""
    if not _RAW:
        etf, _, ai = ev.load()
        d = json.loads((ev.CACHE / "ai.json").read_text())
        _RAW.update(etf=etf[2].daily, etf_names=etf[3], ai=ai[2].daily, stocks=ai[3], groups=d["groups"],
                    entries=d.get("membership", {}).get("entries", []))
        a = _RAW["ai"]   # membership windows, as backtest.load_ai applies them to the closes
        for e in _RAW["entries"]:
            t = e["ticker"]
            for f in [a.close, a.high, a.low, a.volume]:
                if t in f:
                    if e.get("from"):
                        f.loc[f.index < pd.Timestamp(e["from"]), t] = np.nan
                    if e.get("until"):
                        f.loc[f.index >= pd.Timestamp(e["until"]), t] = np.nan
    return _RAW


UNIVERSES = ["AI layers vs QQQ", "AI subsectors vs QQQ", "ETFs vs SPY", "AI stocks vs QQQ"]
_U = {}


def universe(name, end):
    key = (name, end)
    if key in _U:
        return _U[key]
    R = raw()
    if name == "ETFs vs SPY":
        u = Universe(name, "SPY", cut(R["etf"], R["etf_names"] + ["SPY"], end), None, None, end)
    elif name == "AI stocks vs QQQ":
        u = Universe(name, "QQQ", cut(R["ai"], R["stocks"] + ["QQQ"], end), None, None, end)
    else:
        md = cut(R["ai"], R["stocks"] + ["QQQ"], end)
        members = baskets(md, R["groups"], "layer" if "layers" in name else "sub")
        C, H, L, V = basket_bars(md, members)
        q = md.close["QQQ"]
        d = ev.Bars(C.assign(QQQ=q), H.assign(QQQ=md.high["QQQ"]), L.assign(QQQ=md.low["QQQ"]),
                    V.assign(QQQ=md.volume["QQQ"] * q))
        u = Universe(name, "QQQ", d, members, md, end)
    _U[key] = u
    return u


# ---------------------------------------------------------------- the model

def softmax_fit(X, y, K=4, ridge=RIDGE, iters=30):
    """Multinomial logistic regression by Newton's method; last class is the reference."""
    n, p = X.shape
    Y = np.eye(K)[y]
    W = np.zeros((p, K - 1))
    pen = np.full(p, ridge)
    pen[0] = 0
    for _ in range(iters):
        Z = np.c_[X @ W, np.zeros(n)]
        Z -= Z.max(1, keepdims=True)
        P = np.exp(Z)
        P /= P.sum(1, keepdims=True)
        G = (X.T @ (P[:, :-1] - Y[:, :-1])) + pen[:, None] * W
        Hs = np.zeros(((K - 1) * p, (K - 1) * p))
        for a in range(K - 1):
            for c in range(a, K - 1):
                w = P[:, a] * ((a == c) - P[:, c])
                blk = X.T @ (X * w[:, None])
                Hs[a * p:(a + 1) * p, c * p:(c + 1) * p] = blk
                Hs[c * p:(c + 1) * p, a * p:(a + 1) * p] = blk
        Hs += np.diag(np.tile(pen, K - 1)) + 1e-8 * np.eye((K - 1) * p)
        step = np.linalg.solve(Hs, G.T.reshape(-1)).reshape(K - 1, p).T
        W -= step
        if np.abs(step).max() < 1e-6:
            break
    return W


def softmax_predict(W, X):
    Z = np.c_[X @ W, np.zeros(len(X))]
    Z -= Z.max(1, keepdims=True)
    P = np.exp(Z)
    return P / P.sum(1, keepdims=True)


def long(f):
    return f.stack(future_stack=True)


def design(u, inds):
    """Long frame, one row per (week, factor): baseline features, indicator columns, quadrant."""
    Q = long(u.q)
    df = pd.DataFrame({"q": Q, "x": long(u.rsr) - 100, "y": long(u.rsm) - 100,
                       "dx": long(u.rsr.diff()), "dy": long(u.rsm.diff())})
    for i, f in enumerate(inds):
        df[f"f{i}"] = long(f.reindex(index=u.px.index, columns=u.px.columns))
    return df


def base_cols(df):
    X = [df[["dx", "dy"]].to_numpy()]
    for k in range(4):
        m = (df["q"].to_numpy() == k).astype(float)[:, None]
        X += [m, m * df[["x", "y"]].to_numpy()]
    return np.hstack(X)


def ind_cols(df, n_ind, lo=None, hi=None):
    X = []
    for i in range(n_ind):
        v = df[f"f{i}"].to_numpy()
        if lo is not None:
            v = np.clip(v, lo[i], hi[i])
        for k in range(4):
            X.append((df["q"].to_numpy() == k) * v)
    return np.array(X).T if X else np.zeros((len(df), 0))


def walk_forward(u, inds, H, oos_from=None):
    """Out-of-sample class probabilities for the baseline and the candidate on common rows."""
    df = design(u, inds)
    weeks = u.px.index
    pos = pd.Series(np.arange(len(weeks)), index=weeks)
    label = long(u.q.shift(-H))
    df["label"] = label
    df["fwd"] = long(np.log(u.px.div(u.b, axis=0)).shift(-H) - np.log(u.px.div(u.b, axis=0)))
    feats = ["q", "x", "y", "dx", "dy"] + [f"f{i}" for i in range(len(inds))]
    df = df.dropna(subset=feats)
    df = df[np.isfinite(df[feats]).all(axis=1)]
    df["pos"] = pos.reindex(df.index.get_level_values(0)).to_numpy()
    lab = df.dropna(subset=["label"])
    first_lab = lab["pos"].min() if len(lab) else np.inf
    start = first_lab + MIN_TRAIN + H
    if oos_from is not None:
        start = max(start, pos[weeks >= oos_from].min())
    out = []
    n_ind = len(inds)
    for t0 in range(int(start), len(weeks), REFIT):
        tr = lab[lab["pos"] <= t0 - H]
        te = df[(df["pos"] >= t0) & (df["pos"] < t0 + REFIT)].dropna(subset=["label"])
        if len(tr) < 200 or not len(te) or tr["label"].nunique() < 4:
            continue
        lo = [np.nanpercentile(tr[f"f{i}"], 1) for i in range(n_ind)]
        hi = [np.nanpercentile(tr[f"f{i}"], 99) for i in range(n_ind)]
        mats = {}
        for nm, cols in [("base", lambda d: base_cols(d)),
                         ("cand", lambda d: np.hstack([base_cols(d), ind_cols(d, n_ind, lo, hi)]))]:
            Xtr, Xte = cols(tr), cols(te)
            mu, sd = Xtr.mean(0), Xtr.std(0)
            sd[sd == 0] = 1
            Xtr, Xte = np.c_[np.ones(len(Xtr)), (Xtr - mu) / sd], np.c_[np.ones(len(Xte)), (Xte - mu) / sd]
            W = softmax_fit(Xtr, tr["label"].astype(int).to_numpy())
            mats[nm] = softmax_predict(W, Xte)
        o = te[["q", "label", "fwd"]].copy()
        for nm, P in mats.items():
            for k in range(4):
                o[f"{nm}{k}"] = P[:, k]
        out.append(o)
    return pd.concat(out) if out else None


def cell_stats(o, H):
    y = o["label"].astype(int).to_numpy()
    Pb = o[[f"base{k}" for k in range(4)]].to_numpy()
    Pc = o[[f"cand{k}" for k in range(4)]].to_numpy()
    eps = 1e-12
    llb = -np.log(Pb[np.arange(len(y)), y] + eps)
    llc = -np.log(Pc[np.arange(len(y)), y] + eps)
    o = o.assign(llb=llb, llc=llc, d=llb - llc)
    week = o.index.get_level_values(0)
    wk = o.groupby(week)["d"].mean()
    yrs = wk.groupby(wk.index.year).mean()
    clim = np.bincount(y, minlength=4) / len(y)
    # payoff: does the candidate's change to P(right of centre) point the way the price goes?
    dright = (Pc[:, 0] + Pc[:, 1]) - (Pb[:, 0] + Pb[:, 1])
    o = o.assign(dright=dright)
    ic = o.groupby(week).apply(lambda g: g["dright"].rank().corr(g["fwd"].rank()) if len(g) >= 5 else np.nan,
                               include_groups=False)
    per_q = {QUADS[k]: float(o.loc[o["q"] == k, "d"].mean()) for k in range(4)}
    return dict(rows=len(o), weeks=int(wk.size), first=str(wk.index[0].date()), last=str(wk.index[-1].date()),
                ll_clim=float(-(np.log(clim[y] + eps)).mean()), ll_base=float(llb.mean()), ll_cand=float(llc.mean()),
                acc_persist=float((o["q"].to_numpy() == y).mean()), acc_base=float((Pb.argmax(1) == y).mean()),
                acc_cand=float((Pc.argmax(1) == y).mean()),
                skill=float(wk.mean()), skill_t=float(bt.nw_t(wk, H)), yrs_pos=float((yrs > 0).mean()),
                payoff_ic=float(ic.mean()), payoff_t=float(bt.nw_t(ic, H)), skill_by_quadrant=per_q)


# ---------------------------------------------------------------- indicators

def load_library():
    lib = load_file("regime_indicators", HERE / "regime_indicators.py")
    lib.R = sys.modules[__name__]
    return lib


def candidate_hash(lib, names):
    src = "".join(n + inspect.getsource(lib.REGISTRY[n]) for n in sorted(names))
    return hashlib.sha256(src.encode()).hexdigest()[:12], src


def compute(fn, u, check=True):
    """Run one indicator, checking its shape, infinities and look-ahead."""
    f = fn(u)
    if f is None:
        return None
    f = f.reindex(index=u.px.index, columns=u.px.columns).astype(float)
    if np.isinf(f.to_numpy()).any():
        raise ValueError(f"{fn.__name__} returned infinities on {u.name}")
    if f.notna().sum().sum() == 0:
        return None
    if check:
        mid = u.px.index[int(len(u.px.index) * 2 / 3)]
        early = fn(universe(u.name, mid))
        if early is not None:
            a = f.loc[:mid].reindex(columns=early.columns)
            e = early.reindex(index=a.index).astype(float)
            both = a.notna() & e.notna()
            bad = (a[both] - e[both]).abs() > 1e-6 * (1 + a[both].abs())
            if bad.to_numpy().any() or (a.notna() != e.notna()).to_numpy().mean() > 0.01:
                raise ValueError(f"{fn.__name__} changes past values when later data arrives on {u.name} (look-ahead)")
    return f


def score(fns, mode="research", check=True):
    end = HOLDOUT_START - pd.Timedelta(days=1) if mode == "research" else pd.Timestamp("2100-01-01")
    cells = []
    for name in UNIVERSES:
        u = universe(name, end)
        inds = [compute(fn, u, check) for fn in fns]
        if any(f is None for f in inds):
            continue
        for H in HORIZONS:
            o = walk_forward(u, inds, H, HOLDOUT_START if mode == "holdout" else None)
            if o is None or o["label"].nunique() < 4:
                continue
            cells.append(dict(universe=name, horizon=H, **cell_stats(o, H)))
    return cells


def verdict(cells, n_trials):
    unis = {c["universe"] for c in cells}
    if len(unis) < 2:
        return dict(score=float("nan"), bar=float("nan"), forecasts=False, pays=False, passed=False,
                    why=f"defined in {len(unis)} universe(s); needs at least 2")
    s = float(np.mean([c["skill_t"] for c in cells]))
    bar = NormalDist().inv_cdf(1 - 0.05 / max(n_trials, 1))
    why = []
    if s < bar:
        why.append(f"score {s:.2f} < bar {bar:.2f}")
    if any(not c["skill_t"] > 0 for c in cells):
        why.append("skill negative in some cell")
    if any(c["yrs_pos"] < MIN_YEARS_POSITIVE for c in cells):
        why.append(f"positive in < {MIN_YEARS_POSITIVE:.0%} of years in some cell")
    forecasts = not why
    pays = all(c["payoff_ic"] > 0 for c in cells)
    if not pays:
        why.append("forecast changes point the wrong way for returns in some cell")
    return dict(score=s, bar=float(bar), forecasts=forecasts, pays=pays, passed=forecasts and pays,
                why="; ".join(why) or "clears every test")


# ---------------------------------------------------------------- log + output

def read_log(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def show(label, cells, v):
    print(f"\n{label}")
    print(f"{'universe':<22}{'H':>3}{'weeks':>6}{'skill':>9}{'t':>7}{'yrs+':>6}{'payIC':>8}{'t':>6}"
          f"{'acc base':>9}{'cand':>6}   skill by current quadrant (L W Lg I)")
    for c in cells:
        bq = " ".join(f"{c['skill_by_quadrant'][q]:+.3f}" for q in QUADS)
        print(f"{c['universe']:<22}{c['horizon']:>3}{c['weeks']:>6}{c['skill']:>+9.4f}{c['skill_t']:>+7.2f}"
              f"{c['yrs_pos']:>6.0%}{c['payoff_ic']:>+8.3f}{c['payoff_t']:>+6.2f}{c['acc_base']:>9.1%}"
              f"{c['acc_cand']:>6.1%}   {bq}")
    tag = "PASS" if v["passed"] else ("forecasts, doesn't pay" if v["forecasts"] else "fail")
    print(f"score {v['score']:+.2f}  bar {v['bar']:.2f}  {tag}: {v['why']}")


def run(names, mode="research", scratch=False):
    lib = load_library()
    missing = [n for n in names if n not in lib.REGISTRY]
    if missing:
        sys.exit(f"unknown indicator(s) {missing}; see --list")
    h, src = candidate_hash(lib, names)
    if mode == "holdout":
        if h in {r["hash"] for r in read_log(HOLDOUT_LOG)}:
            sys.exit("this candidate already took the holdout; it is finished either way")
        if h not in {r["hash"] for r in read_log(LOG)}:
            sys.exit("score it on the research period first")
    t0 = time.time()
    cells = score([lib.REGISTRY[n] for n in names], mode)
    n = len({r["hash"] for r in read_log(LOG)} | {h})
    v = verdict(cells, n)
    show(f"{' + '.join(names)}  [{mode}, {time.time() - t0:.0f}s, hash {h}, trial {n}]", cells, v)
    rec = dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), mode=mode, names=names, hash=h, cells=cells, **v, source=src)
    if not scratch:
        with open(HOLDOUT_LOG if mode == "holdout" else LOG, "a") as f:
            f.write(json.dumps(rec) + "\n")
    return rec


def baseline():
    """How well do persistence, climatology and the RRG model forecast, per cell."""
    end = HOLDOUT_START - pd.Timedelta(days=1)
    lines = ["# Regime baseline (research period, before 2023)", "",
             "How well the RRG alone forecasts the quadrant H weeks ahead, out of sample. A candidate must",
             "beat the RRG model's log loss. Lower log loss is better; accuracy is the share of correct calls.", "",
             "| universe | H | factors | weeks | log loss: climatology | RRG model | accuracy: stays put | RRG model |",
             "|---|---|---|---|---|---|---|---|"]
    trans = []
    for name in UNIVERSES:
        u = universe(name, end)
        for H in HORIZONS:
            o = walk_forward(u, [], H)
            c = cell_stats(o, H)
            lines.append(f"| {name} | {H} | {u.px.shape[1]} | {c['weeks']} | {c['ll_clim']:.3f} | {c['ll_base']:.3f} "
                         f"| {c['acc_persist']:.1%} | {c['acc_base']:.1%} |")
            print(lines[-1], flush=True)
            if H == 4:
                m = pd.crosstab(o["q"].map(dict(enumerate(QUADS))), o["label"].astype(int).map(dict(enumerate(QUADS))),
                                normalize="index").reindex(index=QUADS, columns=QUADS)
                trans.append((name, m))
    lines += ["", "## Where a quadrant goes in 4 weeks (row = now, column = 4 weeks later)", ""]
    for name, m in trans:
        lines += [f"**{name}**", "", "| now \\ in 4w | " + " | ".join(QUADS) + " |", "|---" * 5 + "|"]
        lines += [f"| {q} | " + " | ".join(f"{m.loc[q, c]:.0%}" for c in QUADS) + " |" for q in QUADS]
        lines.append("")
    (HERE / "regime_baseline.md").write_text("\n".join(lines))
    print("wrote research/regime_baseline.md")


def placebo(k):
    """Random-walk indicators through the full test, not logged. Scores should rarely clear 1.65."""
    rng = np.random.default_rng(11)
    scores = []
    for i in range(k):
        seed = int(rng.integers(1e9))

        def rw(u, seed=seed):
            g = np.random.default_rng(seed + len(u.name))
            idx = raw()["etf"].close.index.union(raw()["ai"].close.index)
            z = pd.DataFrame(g.standard_normal((len(idx), u.px.shape[1])), index=idx, columns=u.px.columns).cumsum()
            return u.weekly(z.loc[:u.end])
        cells = score([rw], check=False)
        v = verdict(cells, 1)
        scores.append(v["score"])
        print(f"placebo {i + 1}: score {v['score']:+.2f}  cells " +
              " ".join(f"{c['skill_t']:+.1f}" for c in cells), flush=True)
    s = np.array(scores)
    print(f"\n{k} placebos: mean {s.mean():+.2f}, 95th pct {np.percentile(s, 95):+.2f}, share > 1.65: {(s > 1.65).mean():.0%}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*")
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--singles", action="store_true")
    ap.add_argument("--placebo", type=int, default=0)
    ap.add_argument("--holdout", action="store_true")
    ap.add_argument("--confirm", action="store_true")
    ap.add_argument("--scratch", action="store_true")
    a = ap.parse_args()
    if a.list:
        lib = load_library()
        for n, fn in lib.REGISTRY.items():
            print(f"{n:<22}{(fn.__doc__ or '').strip().splitlines()[0]}")
    elif a.baseline:
        baseline()
    elif a.placebo:
        placebo(a.placebo)
    elif a.holdout:
        if a.scratch or not a.confirm:
            sys.exit("the holdout is one-shot: pass --confirm, never --scratch")
        run(a.names, "holdout")
    elif a.singles:
        lib = load_library()
        done = {r["hash"] for r in read_log(LOG)}
        for n in lib.REGISTRY:
            if candidate_hash(lib, [n])[0] not in done:
                run([n], scratch=a.scratch)
    elif a.names:
        run(a.names, scratch=a.scratch)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
