"""Deterministic V1.2 fee and risk gates; no live brokerage interaction."""

import csv
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from user_side.personal_experiment.adaptive_learning import V12_PROFILE, _bounded_config
from user_side.personal_experiment.scalping_engine import open_simulated_trade
from user_side.personal_experiment.scalping_net_risk import fee_adjusted_snapshot, v12_entry_allowed
from user_side.personal_experiment.scalping_state import TRADE_FIELDS

NY = ZoneInfo("America/New_York")


def state():
    return {"cash": 1000.0, "positions": {}, "session_start_equity": 1000.0,
            "high_water_mark": 1000.0, "paused": False, "session_date": "2026-11-02",
            "v12_entries_today": 0, "v12_tickers_traded_today": []}


def titan(ticker="TEST"):
    return {"ticker": ticker, "universe": "titan",
            "technical": {"price": 100.0, "atr_pct": 0.009}}


def proposal(ticker="TEST", confidence=0.80):
    return {"ticker": ticker, "side": "LONG", "target_pct": 0.025,
            "confidence": confidence, "rationale": "aligned evidence"}


class V12Controls(unittest.TestCase):
    def test_fee_snapshot_uses_completed_trades(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "trades.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=TRADE_FIELDS)
                writer.writeheader()
                writer.writerow({"session_date": "2026-11-02", "ticker": "TEST",
                                 "side": "LONG", "shares": 2, "entry_price": 100,
                                 "exit_price": 102, "pnl_usd": 4})
            s = state()
            s["cash"] = 1004.0
            snap = fee_adjusted_snapshot(s, 1004.0, day="2026-11-02", trade_log=path)
            self.assertEqual(snap["today_completed_trades"], 1)
            self.assertLess(snap["today_realized_net_usd"], 4)
            self.assertAlmostEqual(snap["net_equity"], 1000 + snap["today_realized_net_usd"], places=3)
            self.assertEqual(snap["today_traded_tickers"], ["TEST"])

    def test_target_latches_after_realized_plus_one(self):
        s = state()
        snap = {"net_equity": 1011, "today_realized_net_pct": 1.1,
                "session_net_return_pct": 1.1, "today_completed_trades": 1,
                "today_traded_tickers": ["TEST"]}
        self.assertFalse(v12_entry_allowed(s, snap, V12_PROFILE))
        self.assertEqual(s["v12_target_hit_session"], "2026-11-02")
        snap["today_realized_net_pct"] = 0.2
        self.assertFalse(v12_entry_allowed(s, snap, V12_PROFILE))

    def test_daily_net_loss_and_net_drawdown_pause(self):
        s = state()
        snap = {"net_equity": 980, "today_realized_net_pct": -1.8,
                "session_net_return_pct": -2.0, "today_completed_trades": 1,
                "today_traded_tickers": ["TEST"]}
        self.assertFalse(v12_entry_allowed(s, snap, V12_PROFILE))
        self.assertTrue(s["paused"])
        s = state()
        s["v12_net_high_water_mark"] = 1000
        snap = {"net_equity": 895, "today_realized_net_pct": 0,
                "session_net_return_pct": 0, "today_completed_trades": 0,
                "today_traded_tickers": []}
        self.assertFalse(v12_entry_allowed(s, snap, V12_PROFILE))
        self.assertTrue(s["paused"])

    def test_microcap_disabled(self):
        s = state()
        micro = {"ticker": "PENNY", "universe": "microcap",
                 "technical": {"price": 0.5, "atr_pct": 0.018}}
        self.assertIsNone(open_simulated_trade(
            state=s, proposal=proposal("PENNY"), candidate=micro,
            now_et=datetime(2026, 11, 2, 10, tzinfo=NY),
            current_equity=1000, risk_equity=677.53, config=V12_PROFILE))

    def test_titan_passes_and_same_ticker_reentry_blocked(self):
        s = state()
        opened = open_simulated_trade(
            state=s, proposal=proposal(), candidate=titan(),
            now_et=datetime(2026, 11, 2, 10, tzinfo=NY),
            current_equity=1000, risk_equity=677.53, config=V12_PROFILE)
        self.assertIsNotNone(opened)
        self.assertEqual(s["v12_entries_today"], 1)
        s["positions"].clear()
        self.assertIsNone(open_simulated_trade(
            state=s, proposal=proposal(), candidate=titan(),
            now_et=datetime(2026, 11, 2, 11, tzinfo=NY),
            current_equity=1000, risk_equity=677.53, config=V12_PROFILE))

    def test_daily_cap_and_confidence_gate(self):
        s = state()
        self.assertIsNone(open_simulated_trade(
            state=s, proposal=proposal(confidence=0.65), candidate=titan(),
            now_et=datetime(2026, 11, 2, 10, tzinfo=NY),
            current_equity=1000, risk_equity=677.53, config=V12_PROFILE))
        s["v12_entries_today"] = 2
        self.assertIsNone(open_simulated_trade(
            state=s, proposal=proposal(), candidate=titan(),
            now_et=datetime(2026, 11, 2, 10, tzinfo=NY),
            current_equity=1000, risk_equity=677.53, config=V12_PROFILE))

    def test_adaptive_review_cannot_loosen_v12_controls(self):
        bounded = _bounded_config(dict(V12_PROFILE), {"changes": {
            "risk_per_trade_pct": 0.01, "max_open_positions": 3,
            "min_confidence": 0.55, "titan_min_target_pct": 0.005,
            "min_cash_reserve_pct": 0.15}})
        self.assertEqual(bounded["risk_per_trade_pct"], 0.005)
        self.assertEqual(bounded["max_open_positions"], 1)
        self.assertEqual(bounded["min_confidence"], 0.72)
        self.assertEqual(bounded["titan_min_target_pct"], 0.02)
        self.assertEqual(bounded["min_cash_reserve_pct"], 0.30)


if __name__ == "__main__":
    unittest.main()
