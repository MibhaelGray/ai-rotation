"""The research loop: Claude proposes a signal, the frozen scorecard judges it, the log remembers.

  python research/agent.py                    5 rounds (needs ANTHROPIC_API_KEY)
  python research/agent.py --rounds 20
  python research/agent.py --dry-run         one round with a canned candidate, nothing logged,
                                              no API call: checks the plumbing

Each round:
  1. Claude gets RULES.md, the signal contract, the baselines and every result so far, and
     returns one complete signal.py as structured JSON (name, idea, hypothesis, code).
  2. The code is checked statically: numpy, pandas, math and statistics imports only, no file,
     process or interpreter access. It runs inside the scorecard's process, so this keeps it
     from reaching the harness; it is a guard against accidents, not a sandbox.
  3. It is saved under research/candidates/, copied to signal.py, and scored by
     research/evaluate.py in a subprocess. The scorecard logs it to log.jsonl and the rising
     bar applies. A look-ahead or crash is fed back next round and is not a trial.
  4. The loop stops at the round budget or at the first PASS. It never runs the holdout:
     that stays a human decision (see RULES.md).

The scorecard files are hashed at start and checked before every round; if either changes, the
loop stops, because the log's results are no longer comparable.
"""
import argparse, ast, hashlib, json, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PY = sys.executable
LOG = HERE / "log.jsonl"
AGENT_LOG = HERE / "agent_log.jsonl"
CANDIDATES = HERE / "candidates"
FROZEN = [HERE / "evaluate.py", ROOT / "scripts" / "backtest.py"]
MODEL = "claude-opus-5-5"
ALLOWED_IMPORTS = {"numpy", "pandas", "math", "statistics"}
BANNED_NAMES = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars",
                "getattr", "setattr", "delattr", "input", "breakpoint", "exit", "quit"}

SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Short unique name, e.g. 'atr stretch 50d inverted'"},
        "idea": {"type": "string", "description": "One sentence: what the signal measures and which way it bets"},
        "hypothesis": {"type": "string", "description": "Why it should work, and what in the results so far led here"},
        "code": {"type": "string", "description": "The complete new research/signal.py, defining NAME, IDEA and signal(px, bench, bars)"},
    },
    "required": ["name", "idea", "hypothesis", "code"],
    "additionalProperties": False,
}

SYSTEM = """You are a quantitative researcher looking for signals that anticipate relative tops and \
bottoms of sectors, industries and stocks 1-3 months ahead. You work inside a fixed experiment: \
you write one candidate signal per round, a frozen scorecard tests it on data before 2023, and every \
attempt raises the bar for the next, so each one should count.

Good rounds:
- Test one clear hypothesis about exhaustion, crowding, participation or trend structure, stated so a \
  failure teaches something. Prefer ideas with an economic reason over parameter tweaks.
- Learn from the log: what has failed, in which universes, with what sign. A signal whose cells \
  disagree in sign is usually two effects mixed together.
- Don't resubmit a near-copy of a logged signal with a different window. Each variant is another \
  trial and lowers everyone's chance of passing.
- Write vectorised pandas/numpy. The scorecard rejects look-ahead (anything that changes past values \
  when later data arrives), so use only rolling/expanding/ewm windows and shift(k) with k >= 0.

Return the whole signal.py file in `code`. It may import only numpy, pandas, math and statistics, \
and must not read or write files."""


# ---------------------------------------------------------------- context

def read_log():
    return [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()] if LOG.exists() else []


def summarise(rec):
    cells = " ".join(f"{c['universe'].split()[0]}{c['horizon']}w={c['ratio']:+.2f}" for c in rec["cells"])
    return (f"- [{rec['kind']}] {rec['name']}: score {rec['score']:+.2f} (bar {rec['bar']:.2f}, "
            f"{'PASS' if rec['passed'] else 'fail'}: {rec['why']}) | {cells}\n  idea: {rec.get('idea', '')}")


def context(feedback):
    log = read_log()
    best = sorted((r for r in log if r.get("source")), key=lambda r: -abs(r["score"]))[:2]
    parts = [
        "# Rules\n" + (HERE / "RULES.md").read_text(),
        "# Current signal.py (the contract and an example)\n```python\n" + (HERE / "signal.py").read_text() + "```",
        "# Baselines\n" + (HERE / "baseline.md").read_text(),
        f"# Every result so far ({len({r['hash'] for r in log})} distinct signals; the next bar is higher)\n"
        + ("\n".join(summarise(r) for r in log) or "(none)"),
    ]
    for r in best:
        parts.append(f"# Source of a strong earlier candidate: {r['name']} (score {r['score']:+.2f})\n"
                     f"```python\n{r['source']}```")
    if feedback:
        parts.append("# Last round\n" + feedback)
    parts.append("Propose the next candidate.")
    return "\n\n".join(parts)


# ---------------------------------------------------------------- checks

def static_check(code):
    """Imports and names a signal may not use. Not a sandbox; see the module docstring."""
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            bad = [m for m in mods if m.split(".")[0] not in ALLOWED_IMPORTS]
            if bad:
                raise ValueError(f"import of {bad} is not allowed (only {sorted(ALLOWED_IMPORTS)})")
        elif isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            raise ValueError(f"use of {node.id}() is not allowed")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError(f"dunder attribute {node.attr} is not allowed")
    names = {t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    if "signal" not in funcs or not {"NAME", "IDEA"} <= names:
        raise ValueError("signal.py must define NAME, IDEA and signal(px, bench, bars)")


def fingerprint():
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in FROZEN}


# ---------------------------------------------------------------- one round

def propose(client, feedback):
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=32000,
        system=SYSTEM,
        messages=[{"role": "user", "content": context(feedback)}],
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        raise RuntimeError(f"model declined: {getattr(msg.stop_details, 'category', None)}")
    if msg.stop_reason == "max_tokens":
        raise RuntimeError("response hit max_tokens before finishing")
    text = next(b.text for b in msg.content if b.type == "text")
    u = msg.usage
    return json.loads(text), dict(input=u.input_tokens, output=u.output_tokens, model=msg.model)


def score(code, scratch):
    CANDIDATES.mkdir(exist_ok=True)
    h = hashlib.sha256(code.encode()).hexdigest()[:12]
    path = CANDIDATES / f"{time.strftime('%Y%m%d-%H%M%S')}_{h}.py"
    path.write_text(code)
    (HERE / "signal.py").write_text(code)
    out = CANDIDATES / f"{path.stem}.json"
    cmd = [PY, str(HERE / "evaluate.py"), str(path), "--json-out", str(out)] + (["--scratch"] if scratch else [])
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, cwd=ROOT)
    if r.returncode or not out.exists():
        err = (r.stderr or r.stdout).strip().splitlines()
        tail = [l for l in err if not re.search(r"delisted|Failed download|^\[|HTTP Error|^\$", l)][-6:]
        return None, path, "\n".join(tail)
    return json.loads(out.read_text()), path, r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    frozen = fingerprint()
    global FATAL
    client, FATAL = None, ()
    if not a.dry_run:
        import anthropic, os
        profile = Path.home() / ".config" / "anthropic"
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN") or profile.exists()):
            sys.exit("No Anthropic credentials in this shell: export ANTHROPIC_API_KEY (or run `ant auth login`) first.")
        client = anthropic.Anthropic()
        FATAL = (anthropic.AuthenticationError, anthropic.PermissionDeniedError, anthropic.BadRequestError,
                 anthropic.NotFoundError)
    feedback, spent = "", dict(input=0, output=0)
    for i in range(1 if a.dry_run else a.rounds):
        if fingerprint() != frozen:
            sys.exit("the scorecard changed during the run; stopping (see RULES.md: a change resets the log)")
        print(f"\n=== round {i + 1} ===", flush=True)
        try:
            if a.dry_run:
                prop = dict(name="dry run", idea="plumbing check", hypothesis="-",
                            code=(HERE / "signal.py").read_text()), {}
            else:
                prop = propose(client, feedback)
        except FATAL as e:
            sys.exit(f"API error that retrying will not fix: {e}")
        except Exception as e:
            print(f"proposal failed: {e}")
            feedback = f"The previous request failed ({e}). Propose again."
            continue
        p, usage = prop
        for k in spent:
            spent[k] += usage.get(k, 0)
        print(f"{p['name']}: {p['idea']}")
        entry = dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), round=i + 1, name=p["name"], idea=p["idea"],
                     hypothesis=p["hypothesis"], usage=usage)
        try:
            static_check(p["code"])
            rec, path, out = score(p["code"], a.dry_run)
        except Exception as e:
            rec, path, out = None, None, str(e)
        entry["file"] = str(path) if path else None
        if rec is None:
            print(f"rejected: {out}")
            entry.update(status="rejected", error=out)
            feedback = (f"`{p['name']}` was rejected before scoring and did not count as a trial:\n{out}\n"
                        "Fix the problem or try a different idea.")
        else:
            print(out.strip().splitlines()[-1])
            entry.update(status="scored", hash=rec["hash"], score=rec["score"], bar=rec["bar"], passed=rec["passed"])
            feedback = f"`{p['name']}` was scored:\n{summarise(rec)}"
        if not a.dry_run:
            with open(AGENT_LOG, "a") as f:
                f.write(json.dumps(entry) + "\n")
        if rec and rec["passed"] and not a.dry_run:
            print(f"\nPASS: {p['name']} clears the bar on the research period. Stopping for human review.\n"
                  f"Read {path}; if it holds up, run the one-shot holdout yourself:\n"
                  f"  python research/evaluate.py --holdout --confirm {path}")
            break
    if not a.dry_run:
        print(f"\ntokens: {spent['input']:,} in, {spent['output']:,} out "
              f"(~${spent['input'] * 4e-6 + spent['output'] * 2e-5:.2f} at Opus 5.5 list prices)")


if __name__ == "__main__":
    main()
