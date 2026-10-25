"""The frozen scorecard for signal research. Research runs edit research/signal.py, never this.

  python research/evaluate.py                 score research/signal.py on the research period
  python research/evaluate.py path/to/sig.py  score another signal file
  python research/evaluate.py --baselines     score the page's existing signals, write baseline.md
  python research/evaluate.py --holdout --confirm path/to/sig.py
                                              the one-shot final exam on the sealed period
  python research/evaluate.py --refresh       re-download the cached data first
  --scratch    score without logging (plumbing tests only; never for real candidates)
  --json-out   also write the result record to a file (research/agent.py reads it)

Universes: ~43 sector and industry ETFs and the 11 SPDR sectors against SPY (weekly, from
1999), and the AI stocks against QQQ (10y fetch). Horizons: 4 and 13 weeks ahead, the range a
top or bottom call is about. Each (universe, horizon) cell reports the rank IC of signal vs
forward relative return with a Newey-West t, the top-minus-bottom-fifth spread net of costs,
and the share of calendar years the spread was positive.

The score is the mean over cells of IC t / placebo t95, where the placebo is the 95th
percentile |t| that persistent random signals reach on the same panel. 1.0 means "as strong
as the luckiest 5% of noise". The bar to PASS rises with the number of distinct signals ever
scored (research/log.jsonl), Bonferroni-style, so trying more ideas makes passing harder.

Research mode sees only dates before HOLDOUT_START: prices are cut there before anything is
computed, so forward returns cannot reach into the sealed period. Holdout mode scores only
dates from HOLDOUT_START on, once per signal, and is logged separately.
"""
import argparse, hashlib, importlib.util, json, os, subprocess, sys, time
from statistics import NormalDist
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))
import backtest as bt  # noqa: E402

HOLDOUT_START = pd.Timestamp("2023-01-01")
HORIZONS = [4, 13]
PLACEBOS = 200
MIN_YEARS_POSITIVE = 0.6
CACHE = HERE / "cache"
LOG = HERE / "log.jsonl"
HOLDOUT_LOG = HERE / "holdout_log.jsonl"
BASELINES = ["rs_ratio b10 e3", "rs_mom b10 e3 m1", "inflection b10 e3", "tenure b10 e3",
             "mom 12w skip0", "mom 12w skip4", "mom 26w skip4", "mom 52w skip4", "voladj 26w skip4"]


# ---------------------------------------------------------------- data

class Bars:
    """OHLCV for one universe, members plus benchmark as columns.

    high, low, volume  weekly (max, min, sum over the week), on the same rows as px
    daily              a Bars-like object with daily close, high, low, volume
    Highs and lows are in the same currency and adjustment as the closes. Volume is in
    shares of the listing (local for foreign names): compare it only with its own history.
    """
    def __init__(self, close, high, low, volume, daily=None):
        self.close, self.high, self.low, self.volume, self.daily = close, high, low, volume, daily

    def take(self, cols, end=None, rows=None):
        """Columns cols, daily rows up to end (inclusive), weekly rows on index rows."""
        d = self.daily
        cut = (lambda f: f.loc[:end, cols]) if end is not None else (lambda f: f[cols])
        daily = Bars(cut(d.close), cut(d.high), cut(d.low), cut(d.volume))
        wk = lambda f: f[cols].reindex(rows)
        return Bars(wk(self.close), wk(self.high), wk(self.low), wk(self.volume), daily)


def ohlcv(symbols, period):
    """Daily adjusted OHLCV from Yahoo, one frame per field, retried like backtest.load_etfs."""
    import yfinance as yf
    out = {}
    for attempt in range(3):
        need = [s for s in symbols if s not in out.get("Close", pd.DataFrame()) or out["Close"][s].dropna().empty]
        if not need:
            break
        try:
            d = yf.download(need, period=period, interval="1d", progress=False, auto_adjust=True, threads=True)
            for f in ["Close", "High", "Low", "Volume"]:
                x = d[f]
                x = x.to_frame(need[0]) if isinstance(x, pd.Series) else x
                x.index = pd.to_datetime([str(i.date()) for i in x.index])
                out[f] = x if f not in out else out[f].combine_first(x)
        except Exception as e:
            print(f"OHLCV download attempt {attempt + 1} failed: {e}", file=sys.stderr)
    missing = [s for s in symbols if s not in out.get("Close", {}) or out["Close"][s].dropna().empty]
    if missing:
        print(f"warning: no OHLCV for {missing}", file=sys.stderr)
    return out


def weekly_bars(close, high, low, volume, rows):
    """Weekly high/low/volume on the given weekly rows, from daily frames."""
    g = lambda f, how: getattr(f.resample("W-FRI"), how)().reindex(rows)
    vol = volume.where(close.notna()).resample("W-FRI").sum(min_count=1).reindex(rows)
    return Bars(close.resample("W-FRI").last().reindex(rows), g(high, "max"), g(low, "min"), vol,
                Bars(close, high, low, volume))


def load(refresh=False):
    """Weekly closes and OHLCV bars for every universe, cached under research/cache/."""
    CACHE.mkdir(exist_ok=True)
    etf_p, ai_p, ai_bars_p = CACHE / "etf_ohlcv.pkl", CACHE / "ai.json", CACHE / "ai_ohlcv.pkl"
    syms = sorted(set(bt.SECTORS + bt.INDUSTRY + ["SPY", "RSP", "QQQ"]))
    if refresh or not etf_p.exists():
        pd.to_pickle(ohlcv(syms, "max"), etf_p)
    if refresh or not ai_p.exists():
        env = dict(os.environ, FETCH_PERIOD="10y", FETCH_OUT=str(ai_p))
        subprocess.run([sys.executable, str(ROOT / "scripts" / "fetch.py")], env=env, check=True)
    d = json.loads(ai_p.read_text())
    fl = json.loads((ROOT / "config" / "baskets.json").read_text()).get("foreign_listings", {})
    # ETFs: the same weekly closes backtest.load_etfs() builds, plus bars from the same download.
    e = {f: x[x.index >= "1999-01-01"].dropna(how="all") for f, x in pd.read_pickle(etf_p).items()}
    etf = bt.weekly(e["Close"])
    etf_bars = weekly_bars(e["Close"], e["High"], e["Low"], e["Volume"], etf.index)

    # AI: fetch.py's USD closes (foreign listings converted, membership windows applied by
    # load_ai). Highs and lows come from the listing's own high/close and low/close ratios,
    # which are currency-free, applied to the USD close.
    bt.DATA = ai_p
    ai, stocks, _ = bt.load_ai()
    if refresh or not ai_bars_p.exists():   # the stocks and QQQ; macro codes are not Yahoo symbols
        pd.to_pickle(ohlcv(sorted({fl.get(t, t) for t in stocks + ["QQQ"]}), "10y"), ai_bars_p)
    a = pd.read_pickle(ai_bars_p)
    idx = pd.to_datetime(d["dates"])
    close = pd.DataFrame({k: pd.Series(v, index=idx, dtype=float) for k, v in d["px"].items()})
    sym = {t: fl.get(t, t) for t in close}
    ratio = lambda f: pd.DataFrame({t: (a[f][s] / a["Close"][s]).reindex(idx) if s in a[f] else np.nan
                                    for t, s in sym.items()}, index=idx)
    high, low = close * ratio("High").clip(lower=1), close * ratio("Low").clip(upper=1)
    vol = pd.DataFrame({t: a["Volume"][s].reindex(idx) if s in a["Volume"] else np.nan
                        for t, s in sym.items()}, index=idx)
    ai_bars = weekly_bars(close, high, low, vol, ai.index)

    ind = [s for s in bt.SECTORS + bt.INDUSTRY if s in etf]
    sec = [s for s in bt.SECTORS if s in etf]
    # (name, weekly closes, bars, members, benchmark, minimum names per date)
    return [("ETFs vs SPY", etf, etf_bars, ind, "SPY", 10),
            ("Sectors vs SPY", etf, etf_bars, sec, "SPY", 8),
            ("AI stocks vs QQQ", ai, ai_bars, stocks, "QQQ", 10)]


def panel(px, bars, members, bench, mode):
    P, b = px[members], px[bench]
    P, b = P[b.notna()], b[b.notna()]
    if mode == "research":
        P, b = P[P.index < HOLDOUT_START], b[b.index < HOLDOUT_START]
    P = P.dropna(axis=1, how="all")
    return P, b, bars.take(list(P.columns) + [bench], end=P.index[-1], rows=P.index)


# ---------------------------------------------------------------- checks

def load_signal(path):
    spec = importlib.util.spec_from_file_location("candidate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    src = Path(path).read_text()
    return mod, hashlib.sha256(src.encode()).hexdigest()[:12]


def check(fn, P, b, bars):
    """Shape and look-ahead checks: a signal must not change its past when the future arrives."""
    s = fn(P, b, bars)
    if not isinstance(s, pd.DataFrame) or not s.index.equals(P.index) or list(s.columns) != list(P.columns):
        raise ValueError("signal() must return a DataFrame with the same index and columns as px")
    if np.isinf(s.to_numpy(dtype=float)).any():
        raise ValueError("signal() returned inf values; return NaN where it is undefined")
    cut = P.index[len(P) * 2 // 3]
    Pc = P[P.index <= cut]
    early = fn(Pc, b[b.index <= cut], bars.take(list(bars.close.columns), end=cut, rows=Pc.index))
    a, c = s[s.index <= cut].to_numpy(dtype=float), early.to_numpy(dtype=float)
    same = np.isclose(a, c, rtol=1e-6, atol=1e-9, equal_nan=True)
    if not same.all():
        raise ValueError(f"look-ahead: {int((~same).sum())} values up to {cut.date()} change when later "
                         "data is added. Use only past and current rows.")
    return s


# ---------------------------------------------------------------- scoring

def placebo_t95(key, P, fwd, H, min_n):
    """95th percentile |IC t| of random-walk signals on this panel; cached per cell."""
    path = CACHE / "placebo.json"
    cache = json.loads(path.read_text()) if path.exists() else {}
    if key not in cache:
        rng = np.random.default_rng(int(hashlib.sha256(key.encode()).hexdigest()[:8], 16))
        ts = []
        for _ in range(PLACEBOS):
            walk = pd.DataFrame(rng.standard_normal(P.shape).cumsum(axis=0), index=P.index,
                                columns=P.columns).where(P.notna())
            _, ic, _, _ = bt.evaluate(walk, fwd, H, min_n)
            ts.append(abs(bt.nw_t(ic, H)))
        cache[key] = float(np.nanpercentile(ts, 95))
        path.write_text(json.dumps(cache, indent=1))
    return cache[key]


def score_cells(fn, universes, mode):
    cells = []
    for name, px, bars, members, bench, min_n in universes:
        P, b, B = panel(px, bars, members, bench, mode)
        sig = check(fn, P, b, B)
        lr = np.log(P.div(b, axis=0))
        for H in HORIZONS:
            fwd = lr.shift(-H) - lr
            if mode == "holdout":
                fwd = fwd[fwd.index >= HOLDOUT_START]
            sp, ic, top, bot = bt.evaluate(sig.reindex(fwd.index), fwd, H, min_n)
            sp, ic = sp.dropna(), ic.dropna()
            if len(ic) < 2 * H + 8:
                continue
            thr = placebo_t95(f"{mode}|{name}|{H}|{P.shape}", P, fwd, H, min_n)
            ic_t = bt.nw_t(ic, H)
            yr = sp.groupby(sp.index.year).mean()
            net = sp.mean() - 2 * bt.COST * (bt.turnover(top, H) + bt.turnover(bot, H))
            cells.append(dict(universe=name, horizon=H, start=str(ic.index[0].date()), end=str(ic.index[-1].date()),
                              dates=len(ic), ic=float(ic.mean()), ic_t=float(ic_t), placebo_t95=thr,
                              ratio=float(ic_t / thr), spread=float(sp.mean()), net=float(net),
                              yrs_pos=float((yr > 0).mean())))
    return cells


def verdict(cells, n_trials):
    """Mean ratio against a bar that rises with the number of distinct signals tried."""
    if not cells:
        return dict(score=float("nan"), bar=float("nan"), passed=False, why="no scorable cells")
    score = float(np.mean([c["ratio"] for c in cells]))
    z = NormalDist().inv_cdf(1 - 0.05 / (2 * max(n_trials, 1)))
    bar = z / NormalDist().inv_cdf(0.975)
    sign = np.sign(score)
    agree = all(np.sign(c["ic"]) == sign for c in cells)
    yrs = np.mean([c["yrs_pos"] if sign > 0 else 1 - c["yrs_pos"] for c in cells])
    why = []
    if abs(score) < bar:
        why.append(f"|score| {abs(score):.2f} < bar {bar:.2f}")
    if not agree:
        why.append("IC sign differs across cells")
    if yrs < MIN_YEARS_POSITIVE:
        why.append(f"right direction in only {yrs:.0%} of years")
    return dict(score=score, bar=float(bar), passed=not why, why="; ".join(why) or "clears every test")


# ---------------------------------------------------------------- log + output

def read_log(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def n_trials(extra_hash):
    return len({r["hash"] for r in read_log(LOG)} | {extra_hash})


def show(name, cells, v):
    print(f"\n{name}")
    print(f"  {'universe':<18}{'H':>4}{'IC':>8}{'IC t':>7}{'pl t95':>8}{'ratio':>7}{'net/H':>9}{'yrs+':>6}")
    for c in cells:
        print(f"  {c['universe']:<18}{c['horizon']:>4}{c['ic']:>+8.3f}{c['ic_t']:>+7.2f}{c['placebo_t95']:>8.2f}"
              f"{c['ratio']:>+7.2f}{100 * c['net']:>+8.2f}%{c['yrs_pos']:>6.0%}")
    print(f"  score {v['score']:+.2f}  bar {v['bar']:.2f}  {'PASS' if v['passed'] else 'fail'}: {v['why']}")


def run_file(path, universes, mode, scratch=False, json_out=None):
    mod, h = load_signal(path)
    name = getattr(mod, "NAME", Path(path).stem)
    if mode == "holdout":
        if any(r["hash"] == h for r in read_log(HOLDOUT_LOG)):
            sys.exit(f"{name} ({h}) has already taken the holdout exam; it is one-shot.")
        if not any(r["hash"] == h for r in read_log(LOG)):
            sys.exit("score this exact file on the research period first.")
    cells = score_cells(mod.signal, universes, mode)
    v = verdict(cells, n_trials(h) if mode == "research" else 1)
    rec = dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), mode=mode, kind="candidate", name=name,
               idea=getattr(mod, "IDEA", ""), hash=h, **v, cells=cells,
               source=Path(path).read_text())
    if not scratch:
        with open(LOG if mode == "research" else HOLDOUT_LOG, "a") as f:
            f.write(json.dumps(rec) + "\n")
    if json_out:
        Path(json_out).write_text(json.dumps(rec))
    show(f"{name}  [{h}, {mode}{', not logged' if scratch else ''}]", cells, v)


def run_baselines(universes):
    rows = []
    for sname in BASELINES:
        fn = lambda P, b, bars, s=sname: bt.signals(P, b)[s][2]
        h = hashlib.sha256(f"baseline:{sname}".encode()).hexdigest()[:12]
        cells = score_cells(fn, universes, "research")
        v = verdict(cells, n_trials(h))
        with open(LOG, "a") as f:
            f.write(json.dumps(dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), mode="research", kind="baseline",
                                    name=sname, idea="existing backtest signal", hash=h, **v, cells=cells)) + "\n")
        show(sname, cells, v)
        rows.append((sname, cells, v))
    w = ["# Baseline scores (research period, before " + str(HOLDOUT_START.date()) + ")\n",
         "Score = mean over cells of IC t / placebo t95. A new signal has to beat these, and the bar.\n",
         "| Signal | Score | " + " | ".join(f"{c['universe']} {c['horizon']}w" for c in rows[0][1]) + " | Verdict |",
         "|---|---|" + "---|" * len(rows[0][1]) + "---|"]
    for sname, cells, v in sorted(rows, key=lambda r: -abs(r[2]["score"])):
        w.append(f"| {sname} | {v['score']:+.2f} | " + " | ".join(f"{c['ratio']:+.2f}" for c in cells)
                 + f" | {'PASS' if v['passed'] else 'fail'} |")
    (HERE / "baseline.md").write_text("\n".join(w) + "\n")
    print(f"\nwrote {HERE / 'baseline.md'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("signal", nargs="?", default=str(HERE / "signal.py"))
    ap.add_argument("--baselines", action="store_true")
    ap.add_argument("--holdout", action="store_true")
    ap.add_argument("--confirm", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--scratch", action="store_true")
    ap.add_argument("--json-out")
    a = ap.parse_args()
    if a.holdout and a.scratch:
        sys.exit("--scratch is for the research period only; the holdout is always logged.")
    if a.holdout and not a.confirm:
        sys.exit("--holdout spends the one-shot exam for this signal; add --confirm if you mean it.")
    universes = load(a.refresh)
    if a.baselines:
        run_baselines(universes)
    else:
        run_file(a.signal, universes, "holdout" if a.holdout else "research", a.scratch, a.json_out)


if __name__ == "__main__":
    main()
