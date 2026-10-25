"""Rencana trade. calc_tp_sl = INTI MATEMATIKA TP/SL (DIBEKUKAN, jangan diubah tanpa versi baru).
Catatan: kode tn asli tidak ada di zip; rumus di sini turunan Mesin 2 versi DeepSeek (SL = kelipatan ATR per pola, maks 15%, TP = rr x risiko)."""
SL_ATR = {"fib": 1.0, "dd": 1.2, "mon": 1.5, "zone": 1.2, "dev": 1.3, "bo": 1.5, "wolf": 1.5}
def calc_tp_sl(side, entry, atr, trig, rr):
    sl = entry - side * SL_ATR.get(trig, 1.5) * atr
    sl = max(sl, entry * .85) if side == 1 else min(sl, entry * 1.15)
    risk = abs(entry - sl); return sl, entry + side * rr * risk, risk
def tp_already_hit(side, tp, since_df):
    """True bila TP sudah tersentuh sejak waktu keputusan (mencegah setup 'lahir mati')."""
    if since_df is None or since_df.empty: return False
    return bool(since_df.h.max() >= tp) if side == 1 else bool(since_df.l.min() <= tp)
def build(base, sym_src, f, px, decision_ms, qv, since_df, cfg):
    g = cfg["guards"]; side = f["side"]; entry = min(f["lvl"], px) if side == 1 else max(f["lvl"], px)
    sl, tp, risk = calc_tp_sl(side, entry, f["atr"], f["trig"], cfg["rr"])
    if not base or risk <= 0: return None, "NO_SYMBOL_OR_RISK"
    if risk / entry * 100 > g["max_sl_pct"]: return None, "SL_TOO_WIDE"
    if abs(px - entry) / f["atr"] > g["max_entry_dist_atr"]: return None, "ENTRY_TOO_FAR"            # -> watchlist, bukan setup
    if side * (tp - px) <= 0 or tp_already_hit(side, tp, since_df): return None, "TP_ALREADY_PASSED"
    r = cfg["risk"]; qty = r["equity"] * r["risk_pct"] / 100 / risk
    return dict(symbol=base, pair=f"{base}/{cfg['quote']}", source=sym_src, decision_ms=decision_ms, side="LONG" if side == 1 else "SHORT",
                entry=entry, sl=sl, tp=tp, rr=cfg["rr"], risk_pct=risk / entry * 100, qty=qty, trig=f["trig"], why=f["why"], conf=f["conf"],
                px_at_decision=px, qv=qv, due_ms=decision_ms + cfg["max_hold_days"] * 864e5), "OK"
def portfolio_filter(cands, open_setups, cfg):
    """Batasi korelasi: maks posisi, maks searah, total risiko terbuka (1 aset = 1 order aktif)."""
    r = cfg["risk"]; held = {s["symbol"] for s in open_setups}; n = len(open_setups); same = {"LONG": 0, "SHORT": 0}
    for s in open_setups: same[s["side"]] += 1
    tot = n * r["risk_pct"]; out = []
    for s in sorted(cands, key=lambda s: (-s["conf"], s["risk_pct"])):
        if s["symbol"] in held or n >= r["max_open"] or same[s["side"]] >= r["max_same_dir"] or tot + r["risk_pct"] > r["max_total_risk_pct"]: continue
        out.append(s); held.add(s["symbol"]); n += 1; same[s["side"]] += 1; tot += r["risk_pct"]
    return out
