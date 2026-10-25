"""Data: universe dinamis (tanpa hardcode) + OHLCV dengan failover antar-exchange, paralel (ekstraksi dari Grok)."""
import re, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
_EX = {}
def ex(name):
    import ccxt
    if name not in _EX:
        e = getattr(ccxt, name)({"enableRateLimit": True, "timeout": 20000, "options": {"fetchCurrencies": False}})
        if name == "binance":   # endpoint data publik yang tidak diblokir untuk IP runner (dipakai benchmark sebelumnya)
            e.urls["api"] = {**e.urls["api"], "public": "https://data-api.binance.vision/api/v3", "private": "https://data-api.binance.vision/api/v3"}
        _EX[name] = e
    return _EX[name]
def universe(cfg):
    """Semua pair spot aktif quote USDT dari tiap exchange, digabung per base; sumber = exchange dengan volume terbesar."""
    best, rx = {}, re.compile(cfg["exclude_regex"])
    for name in cfg["exchanges"]:
        try:
            e = ex(name); mk = e.load_markets(); tk = e.fetch_tickers()
        except Exception as err:
            print(f"[universe] {name} gagal: {err}"); continue
        for sym, m in mk.items():
            if not (m.get("spot") and m.get("active", True) and m.get("quote") == cfg["quote"] and m.get("base")) or rx.search(sym): continue
            t = tk.get(sym) or {}; qv = t.get("quoteVolume") or ((t.get("baseVolume") or 0) * (t.get("last") or 0))
            if qv >= cfg["min_quote_volume_usd"] and qv > best.get(m["base"], (0,))[0]: best[m["base"]] = (qv, name, sym)
    if not best: raise RuntimeError("Universe kosong: semua exchange gagal/diblokir dari lokasi runner. Ubah 'exchanges' di config.json.")
    rows = sorted(((b, v[1], v[2], v[0]) for b, v in best.items()), key=lambda r: -r[3])
    return rows[: cfg["max_symbols"]] if cfg.get("max_symbols") else rows
def ohlcv(base, prefer, cfg, tf=None, limit=400, since=None):
    """Exchange sumber dulu, lalu exchange lain. DataFrame t,o,h,l,c,v (ms UTC) atau None."""
    for name in [prefer] + [n for n in cfg["exchanges"] if n != prefer]:
        try:
            r = ex(name).fetch_ohlcv(f"{base}/{cfg['quote']}", tf or cfg["timeframe"], since=since, limit=limit)
            if len(r) > 10: return pd.DataFrame(r, columns=["t", "o", "h", "l", "c", "v"])
        except Exception: time.sleep(.2)
    return None
def fetch_all(rows, cfg):
    with ThreadPoolExecutor(cfg["workers"]) as p:
        return dict(zip([r[0] for r in rows], p.map(lambda r: ohlcv(r[0], r[1], cfg), rows)))
