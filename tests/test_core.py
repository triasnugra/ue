import unittest, pandas as pd
from engine import evaluate as ev, journal, plan
CFG = {"entry_ttl_hours": 72, "costs": {"fee_pct_side": .05, "slip_pct": .05}}
H = 36e5; T0 = 1_000_000 * H
S = dict(side="LONG", entry=100., sl=95., tp=110., decision_ms=int(T0), due_ms=int(T0 + 7 * 24 * H))
def df(rows): return pd.DataFrame([dict(t=int(T0 + i * H), o=o, h=h, l=l, c=c) for i, (o, h, l, c) in enumerate(rows)])
class T(unittest.TestCase):
    def test_tp_before_entry_is_expired_with_tp_time(self):
        r = ev.evaluate(S, df([(104, 111, 103, 110), (110, 111, 99, 100)]), CFG, int(T0 + 9 * H))
        self.assertEqual((r["status"], r["reason"], r["result_ms"]), ("EXPIRED", "TP_BEFORE_ENTRY", int(T0)))
    def test_normal_tp_is_chronological(self):
        r = ev.evaluate(S, df([(104, 105, 99, 101), (101, 111, 100, 110)]), CFG, int(T0 + 9 * H))
        self.assertEqual(r["status"], "TP"); self.assertLessEqual(r["entry_ms"], r["result_ms"]); self.assertGreater(r["R_net"], 1.9 - .2)
    def test_candle_before_decision_ignored(self):
        c = pd.concat([pd.DataFrame([dict(t=int(T0 - H), o=100, h=120, l=99, c=100)]), df([(104, 105, 103, 104)])])
        self.assertEqual(ev.evaluate(S, c, CFG, int(T0 + 9 * H))["status"], "PENDING")
    def test_guard_tp_already_hit(self):
        self.assertTrue(plan.tp_already_hit(1, 110, df([(100, 111, 99, 100)]))); self.assertFalse(plan.tp_already_hit(-1, 90, df([(100, 111, 99, 100)])))
    def test_legacy_recovery(self):
        ok, _ = journal.recover_legacy(dict(id="2026-10-20|Aturan Eliz|NEAR", arah="LONG", entry=4.69, sl=4.5, tp=5.05)); self.assertEqual(ok["symbol"], "NEAR")
        bad, why = journal.recover_legacy(dict(id="", side="LONG", entry=1, sl=.9, tp=1.2, t=1)); self.assertIsNone(bad); self.assertEqual(why, "SYMBOL_UNRECOVERABLE")
if __name__ == "__main__": unittest.main()
