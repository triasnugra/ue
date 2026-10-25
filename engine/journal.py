"""Jurnal append-only berantai hash + pemulihan setup lama (memperbaiki status Invalid / simbol kosong)."""
import hashlib, json, os, re
def load(path):
    return [json.loads(l) for l in open(path) if l.strip()] if os.path.exists(path) else []
def append(path, setup):
    rows = load(path); prev = rows[-1]["h"] if rows else "GENESIS"; setup = {**setup, "seq": len(rows) + 1, "prev": prev}
    setup["id"] = f"{setup['decision_ms']}|{setup['symbol']}|{setup['side']}"
    if any(r["id"] == setup["id"] for r in rows): return None                    # idempoten
    setup["h"] = hashlib.sha256((prev + json.dumps(setup, sort_keys=True)).encode()).hexdigest()[:20]
    open(path, "a").write(json.dumps(setup) + "\n"); return setup
def verify(path):
    prev = "GENESIS"
    for r in load(path):
        h = r.pop("h"); 
        if r["prev"] != prev or hashlib.sha256((prev + json.dumps(r, sort_keys=True)).encode()).hexdigest()[:20] != h: return False
        prev = h
    return True
_ID = re.compile(r"^(\d{4}-\d{2}-\d{2})\|(?:[^|]*\|)?([A-Z0-9]{2,15})(?:\||$)")
def recover_legacy(row):
    """Setup impor lama: pulihkan simbol (ticker/symbol/aset/id) dan waktu analisis (decision/t/waktu).
    Bila tidak bisa dipulihkan -> (None, alasan): dibuang ke karantina, TIDAK dihitung statistik. Mengembalikan (setup, reason)."""
    sym = (row.get("symbol") or row.get("ticker") or row.get("aset") or "").upper().replace("USDT", "").replace("/", "").strip()
    m = _ID.match(str(row.get("id", "")))
    if not sym and m: sym = m.group(2)
    t = row.get("decision_ms") or row.get("t") or None
    if not t and m: 
        import datetime as d; t = int(d.datetime.fromisoformat(m.group(1)).replace(tzinfo=d.timezone.utc).timestamp() * 1000)
    if not sym: return None, "SYMBOL_UNRECOVERABLE"
    if not t: return None, "ANALYSIS_TIME_UNKNOWN"
    side = str(row.get("side") or row.get("arah") or row.get("direction") or "").upper()
    if side not in ("LONG", "SHORT"): return None, "SIDE_UNKNOWN"
    try: e, sl, tp = (float(row.get(k)) for k in ("entry", "sl", "tp"))
    except (TypeError, ValueError): return None, "PRICES_MISSING"
    return dict(symbol=sym, pair=f"{sym}/USDT", side=side, entry=e, sl=sl, tp=tp, decision_ms=int(t), due_ms=int(t) + 7 * 864e5, legacy=True), "OK"
