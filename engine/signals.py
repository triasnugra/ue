"""Sinyal: fondasi Mesin 2 (scan harian di open, tanpa melihat candle berjalan) + filter risiko DeepSeek.
Wolf sengaja tidak diport (0 menang dari 14 trade; diblokir DeepSeek)."""
import numpy as np, pandas as pd
sgn = lambda p, a, b: 1 if p > b and a > b else -1 if p < b and a < b else 0
def _rsi(c, n=14):
    d = c.diff(); g = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); l = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + g / l.replace(0, 1e-9))
def _obv(x): return (np.sign(x.c.diff().fillna(0)) * x.v).cumsum()
def _div(p, d):
    p, d = p.values, d.values; n = len(p)
    l1 = n-15+int(np.argmin(p[n-15:])); l0 = n-30+int(np.argmin(p[n-30:n-15])); h1 = n-15+int(np.argmax(p[n-15:])); h0 = n-30+int(np.argmax(p[n-30:n-15]))
    return 1 if p[l1] < p[l0] and d[l1] > d[l0] else -1 if p[h1] > p[h0] and d[h1] < d[h0] else 0
def scan_input(df, now_ms):
    """Candle harian tertutup + candle berjalan yang HANYA berisi open (aturan scanInput Mesin 2)."""
    closed, forming = df[df.t + 864e5 <= now_ms], df[df.t + 864e5 > now_ms]
    if closed.empty or forming.empty: return None
    f = forming.iloc[-1]; last = closed.iloc[-1]
    return closed.iloc[-999:].reset_index(drop=True), float(f.o), int(f.t), float(last.v * last.c)
def features(x, px, cfg):
    n = len(x)
    if n < 120: return None
    c = x.c; td = sgn(px, c.ewm(span=20, adjust=False).mean().iloc[-1], c.ewm(span=50, adjust=False).mean().iloc[-1]); tr = td
    w = x.set_index(pd.to_datetime(x.t, unit="ms")).c.resample("W-SUN").last().iloc[:-1]
    if len(w) >= 55: tr = sgn(px, w.ewm(span=20, adjust=False).mean().iloc[-1], w.ewm(span=50, adjust=False).mean().iloc[-1])
    pr, rec = x.iloc[n-65:n-5], x.iloc[n-5:]; H, L = pr.h.max(), pr.l.min(); pos = (px - L) / (H - L); mid = .3 < pos < .7; flat = (H - L) / L < .06
    pc = x.c.shift(); atr = float(np.maximum.reduce([x.h - x.l, (x.h - pc).abs(), (x.l - pc).abs()])[-14:].mean()); bd = min(.6 * atr, (H - L) / 4)
    devUp = px > L and bool(((rec.l < L) & (rec.c > L)).any()); devDn = px < H and bool(((rec.h > H) & (rec.c < H)).any())
    boUp = bool((c.iloc[-10:] > H).any()) and H < px < H * 1.03; boDn = bool((c.iloc[-10:] < L).any()) and L * .97 < px < L
    ww = x.iloc[-60:]; hh, lo = ww.h.max(), ww.l.min(); f75 = hh - .75*(hh-lo) if tr >= 0 else lo + .75*(hh-lo); nf = abs(px - f75) / px < .03
    mi = next((i for i in range(n-1, n-8, -1) if pd.Timestamp(x.t[i], unit="ms").dayofweek == 0), None); mUp = mDn = False; monL = monH = None
    if mi is not None:
        monL, monH, aft = x.l[mi], x.h[mi], x.iloc[mi+1:]
        mUp = px > monL and bool(((aft.l < monL) & (aft.c > monL)).any()); mDn = px < monH and bool(((aft.h > monH) & (aft.c < monH)).any())
    Zs, Zh = c.iloc[-90:].min(), c.iloc[-90:].max(); ls, hs = x.l.values, x.h.values
    def sweeps(arr, z, up):
        S = []
        for i in range(n-60, n):
            if (arr[i] < z*.998 and c[i] > z) if up else (arr[i] > z*1.002 and c[i] < z):
                if not S or i - S[-1] >= 3: S.append(i)
        return S
    sU, sD = sweeps(ls, Zs, True), sweeps(hs, Zh, False)
    ddUp = len(sU) >= 2 and sU[-1] >= n-10 and ls[sU[-1]] > ls[sU[-2]] and px > Zs; ddDn = len(sD) >= 2 and sD[-1] >= n-10 and hs[sD[-1]] < hs[sD[-2]] and px < Zh
    piv = lambda a, i, hi: all((a[j] <= a[i]) if hi else (a[j] >= a[i]) for j in range(i-3, i+4) if j != i)
    tL = sum(1 for i in range(n-65, n-5) if piv(ls, i, 0) and ls[i] <= L*1.02); tH = sum(1 for i in range(n-65, n-5) if piv(hs, i, 1) and hs[i] >= H*.98)
    zUp = tr == 1 and tL >= 2 and L <= px <= L + 1.5*bd and not devUp; zDn = tr == -1 and tH >= 2 and H - 1.5*bd <= px <= H and not devDn
    dR, dO = _div(c, _rsi(c)), _div(c, _obv(x))
    LS = [(t, v, w_) for t, v, w_, ok in [("dd", Zs, "Double Deviation bawah", ddUp), ("dev", L, "Deviasi bawah lalu reclaim", devUp), ("mon", monL, "Sweep Monday Low", mUp), ("zone", L+bd, "Retest demand kuat", zUp), ("bo", H, "Breakout-retest", boUp), ("fib", f75, "Fib 0.75 tren naik", tr == 1 and nf)] if ok]
    SS = [(t, v, w_) for t, v, w_, ok in [("dd", Zh, "Double Deviation atas", ddDn), ("dev", H, "Deviasi atas gagal bertahan", devDn), ("mon", monH, "Sweep Monday High", mDn), ("zone", H-bd, "Retest supply kuat", zDn), ("bo", L, "Breakdown-retest", boDn), ("fib", f75, "Fib 0.75 tren turun", tr == -1 and nf)] if ok]
    side, S = (1, LS) if LS and (not SS or len(LS) > len(SS)) else (-1, SS) if SS else (0, [])
    rev = {1: (devUp, mUp, ddUp), -1: (devDn, mDn, ddDn)}
    if flat or not side or (tr == -side and not any(rev[side])) or (mid and not any(rev[side])): return None
    conf = int(rev[side][0] or rev[side][2]) + int(dR == side) + int(dO == side) + int(tr == side) + int(rev[side][1])
    if conf < cfg["guards"]["min_confirmations"] or (len(S) == 1 and S[0][0] == "mon" and not (dR == side or dO == side)): return None
    trig, lvl, why = sorted(S, key=lambda s: ["dd", "dev", "mon", "zone", "bo", "fib"].index(s[0]))[0]
    return dict(side=side, trig=trig, lvl=float(lvl), why=why, atr=atr, tr=int(tr), conf=conf, pos=float(pos))
