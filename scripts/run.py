"""python -m scripts.run [--mode auto|scan|evaluate]. auto: scan bila belum ada scan hari UTC ini, selalu evaluate."""
import json, os, sys, time, datetime as dt
import pandas as pd
from engine import data, signals, plan, evaluate as ev, journal
CFG = json.load(open("config.json")); J, RES, OUT = "data/journal.jsonl", "data/results.json", "web/data/state.json"
def now(): return int(time.time() * 1000)
def scan(meta):
    rows = data.universe(CFG); print(f"[scan] universe {len(rows)} koin; teratas: {[(r[0], r[1], round(r[3]/1e6)) for r in rows[:5]]}"); allc = data.fetch_all(rows, CFG); src = {r[0]: r[1] for r in rows}
    held = [s for s in journal.load(J) if json.load(open(RES)).get(s["id"], {}).get("status", "PENDING") in ("PENDING", "IN_TRADE")] if os.path.exists(RES) else []
    cands, rej = [], {}
    for base, df in allc.items():
        if df is None: continue
        si = signals.scan_input(df, now())
        if not si: continue
        x, px, dms, qv = si; f = signals.features(x, px, CFG)
        if not f: continue
        since = data.ohlcv(base, src[base], CFG, tf="1h", limit=48, since=dms)
        s, why = plan.build(base, src[base], f, px, dms, qv, since, CFG)
        if s: cands.append(s)
        else: rej[why] = rej.get(why, 0) + 1
    new = [journal.append(J, s) for s in plan.portfolio_filter(cands, held, CFG)]
    meta.update(universe=len(rows), candidates=len(cands), published=sum(1 for n in new if n), rejected=rej, last_scan_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
def evaluate_all(meta):
    res = json.load(open(RES)) if os.path.exists(RES) else {}; byb = {}
    for s in journal.load(J):
        if res.get(s["id"], {}).get("status") in ("TP", "SL", "TIMEOUT", "EXPIRED", "INVALID", "AMBIGUOUS"): continue
        c = data.ohlcv(s["symbol"], s["source"], CFG, tf="1h", limit=1000, since=int(s["decision_ms"]))
        if c is not None: res[s["id"]] = ev.evaluate(s, c, CFG, now())
    json.dump(res, open(RES, "w"))
def publish(meta):
    J_, res = journal.load(J), json.load(open(RES)) if os.path.exists(RES) else {}
    rows = [{**s, **res.get(s["id"], {"status": "PENDING"})} for s in J_]; done = [r for r in rows if r["status"] in ("TP", "SL", "TIMEOUT")]
    n = len(done); tp = sum(r["status"] == "TP" for r in done)
    stats = dict(published=len(rows), resolved=n, tp=tp, sl=sum(r["status"] == "SL" for r in done), expired=sum(r["status"] == "EXPIRED" for r in rows),
                 win_rate=tp / n if n else None, expectancy_R_net=sum(r["R_net"] for r in done) / n if n else None, chain_ok=journal.verify(J),
                 note="Angka tidak sah sebelum >=150 trade dan >=20 minggu (protokol).")
    json.dump(dict(meta=meta, stats=stats, setups=rows[-300:][::-1]), open(OUT, "w"))
if __name__ == "__main__":
    os.makedirs("data", exist_ok=True); os.makedirs("web/data", exist_ok=True)
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "auto"
    meta = json.load(open(OUT))["meta"] if os.path.exists(OUT) else {}; today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    if mode == "scan" or (mode == "auto" and not str(meta.get("last_scan_utc", "")).startswith(today)): scan(meta)
    if mode in ("auto", "evaluate", "scan"): evaluate_all(meta)
    publish(meta)
