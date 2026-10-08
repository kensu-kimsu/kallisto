import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from user_side.personal_experiment.scalping_api_costs import calculate_cost
from user_side.personal_experiment.scalping_engine import (
    evaluate_bar,
    open_simulated_trade,
    stop_pct,
)
from user_side.personal_experiment.scalping_session_runner import SEGMENTS
from user_side.personal_experiment.scalping_strategy import validate_proposals
from user_side.personal_experiment.scalping_v1 import decision_due

NY = ZoneInfo("America/New_York")


class ScalpingSmokeTests(unittest.TestCase):
    def test_stop_bounds(self):
        self.assertEqual(stop_pct("microcap", 0.0001), 0.006)
        self.assertEqual(stop_pct("microcap", 0.10), 0.018)
        self.assertEqual(stop_pct("titan", 0.0001), 0.003)
        self.assertEqual(stop_pct("titan", 0.10), 0.009)

    def test_valid_proposal_filtering(self):
        payload = {
            "trades": [
                {"ticker": "AAPL", "side": "LONG", "target_pct": 0.006, "confidence": 0.70, "rationale": "valid"},
                {"ticker": "MSFT", "side": "SHORT", "target_pct": 0.003, "confidence": 0.80, "rationale": "target too small"},
                {"ticker": "NVDA", "side": "LONG", "target_pct": 0.008, "confidence": 0.40, "rationale": "confidence too low"},
            ]
        }
        result = validate_proposals(payload, {"AAPL", "MSFT", "NVDA"})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["ticker"], "AAPL")

    def test_position_risk_sizing(self):
        state = {
            "cash": 1000.0,
            "positions": {},
            "session_start_equity": 1000.0,
            "high_water_mark": 1000.0,
            "paused": False,
        }
        proposal = {
            "ticker": "TEST",
            "side": "LONG",
            "target_pct": 0.01,
            "confidence": 0.75,
            "rationale": "smoke test",
        }
        candidate = {
            "ticker": "TEST",
            "universe": "titan",
            "technical": {"price": 100.0, "atr_pct": 0.005},
        }
        opened = open_simulated_trade(
            state=state,
            proposal=proposal,
            candidate=candidate,
            now_et=datetime(2026, 10, 8, 10, 0, tzinfo=NY),
            current_equity=1000.0,
        )
        self.assertIsNotNone(opened)
        notional = opened["shares"] * opened["entry_price"]
        risk = opened["shares"] * abs(opened["entry_price"] - opened["stop_price"])
        self.assertLessEqual(notional, 300.01)
        self.assertLessEqual(risk, 5.01)
        self.assertGreaterEqual(state["cash"], 150.0)

    def test_same_bar_stop_is_conservative(self):
        pos = {
            "side": "LONG",
            "entry_price": 100.0,
            "stop_price": 99.0,
            "initial_stop_price": 99.0,
            "target_price": 101.0,
            "opened_at": datetime(2026, 10, 8, 10, 0, tzinfo=NY).isoformat(),
            "breakeven_armed": False,
        }
        bar = {"high": 101.5, "low": 98.5, "close": 100.5}
        price, reason = evaluate_bar(pos, bar, datetime(2026, 10, 8, 10, 5, tzinfo=NY))
        self.assertEqual(price, 99.0)
        self.assertEqual(reason, "STOP_FIRST_SAME_BAR")

    def test_time_stop(self):
        opened = datetime(2026, 10, 8, 10, 0, tzinfo=NY)
        pos = {
            "side": "LONG",
            "entry_price": 100.0,
            "stop_price": 99.0,
            "initial_stop_price": 99.0,
            "target_price": 102.0,
            "opened_at": opened.isoformat(),
            "breakeven_armed": False,
        }
        bar = {"high": 100.6, "low": 99.5, "close": 100.2}
        price, reason = evaluate_bar(pos, bar, opened + timedelta(minutes=75))
        self.assertEqual(price, 100.2)
        self.assertEqual(reason, "TIME_STOP")

    def test_decision_cadence(self):
        now = datetime(2026, 10, 8, 10, 0, tzinfo=NY)
        self.assertTrue(decision_due({"last_decision_et": None}, now))
        self.assertFalse(decision_due({"last_decision_et": (now - timedelta(minutes=14)).isoformat()}, now))
        self.assertTrue(decision_due({"last_decision_et": (now - timedelta(minutes=15)).isoformat()}, now))

    def test_session_segments_cover_market(self):
        morning_start, morning_end = SEGMENTS["morning"]
        afternoon_start, afternoon_end = SEGMENTS["afternoon"]
        self.assertLessEqual(morning_start.hour * 60 + morning_start.minute, 9 * 60 + 25)
        self.assertEqual(morning_end, afternoon_start)
        self.assertGreaterEqual(afternoon_end.hour * 60 + afternoon_end.minute, 16 * 60)

    def test_api_cost_math(self):
        cost = calculate_cost("gpt-5.6-luna", 10_000, 2_000, 500)
        expected = (8_000 / 1_000_000 * 0.20) + (2_000 / 1_000_000 * 0.02) + (500 / 1_000_000 * 1.20)
        self.assertAlmostEqual(cost["total_cost_usd"], expected, places=10)


if __name__ == "__main__":
    unittest.main()
