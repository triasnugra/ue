"""Evaluator KRONOLOGIS. Hanya candle dengan open_time >= decision_ms yang dipakai; entry harus <= hasil.
Memperbaiki 'Expired salah': TP yang tersentuh SEBELUM entry terisi -> EXPIRED dengan waktu TP-nya, bukan entry di belakang waktu TP."""
def evaluate(s, c, cfg, now_ms):
    """s: setup; c: DataFrame candle (t,o,h,l,c) interval kecil (1h/15m). Kembalikan dict status."""
    L = s["side"] == "LONG"; e, sl, tp = s["entry"], s["sl"], s["tp"]; risk = abs(e - sl); ttl = s["decision_ms"] + cfg["entry_ttl_hours"] * 36e5
    c = c[c.t >= s["decision_ms"]].sort_values("t"); fill_t = None; fill_px = e
    if risk <= 0: return dict(status="INVALID", reason="ZERO_RISK")
    for k in c.itertuples():
        t_end = k.t + (c.t.iloc[1] - c.t.iloc[0] if len(c) > 1 else 36e5)
        if t_end > now_ms: break                                        # candle belum tutup tidak dipakai
        touch = k.l <= e if L else k.h >= e; tp_hit = k.h >= tp if L else k.l <= tp; sl_hit = k.l <= sl if L else k.h >= sl
        if fill_t is None:
            if tp_hit and not touch: return dict(status="EXPIRED", reason="TP_BEFORE_ENTRY", result_ms=int(k.t))
            if k.t >= ttl: return dict(status="EXPIRED", reason="ENTRY_TTL", result_ms=int(k.t))
            if not touch: continue
            fill_t = int(k.t); fill_px = k.o if (k.o <= e if L else k.o >= e) else e
            if sl_hit: return _done(s, "SL", fill_t, int(k.t), fill_px, risk, cfg)
            if tp_hit: return dict(status="AMBIGUOUS", reason="ENTRY_AND_TP_SAME_CANDLE", entry_ms=fill_t)   # urutan tak bisa dipastikan
            continue
        if sl_hit: return _done(s, "SL", fill_t, int(k.t), fill_px, risk, cfg)
        if tp_hit: return _done(s, "TP", fill_t, int(k.t), fill_px, risk, cfg)
        if k.t >= s["due_ms"]:
            return _done(s, "TIMEOUT", fill_t, int(k.t), fill_px, risk, cfg, close=k.c)
    return dict(status="IN_TRADE" if fill_t else "PENDING", entry_ms=fill_t)
def _done(s, res, fill_t, t, fill_px, risk, cfg, close=None):
    if not (s["decision_ms"] <= fill_t <= t): return dict(status="INVALID", reason="CHRONOLOGY_ERROR")
    sd = 1 if s["side"] == "LONG" else -1; px = s["tp"] if res == "TP" else s["sl"] if res == "SL" else close
    c = cfg["costs"]; cost = (2 * c["fee_pct_side"] + c["slip_pct"]) / 100 * fill_px / risk
    return dict(status=res, entry_ms=fill_t, result_ms=t, entry_px=float(fill_px), R_gross=sd * (px - fill_px) / risk, R_net=sd * (px - fill_px) / risk - cost)
