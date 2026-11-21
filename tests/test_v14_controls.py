"""V1.4 isolation, model instructions and deterministic stop regression tests."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch
from user_side.personal_experiment import scalping_v14
from user_side.personal_experiment.scalping_engine import evaluate_bar
from user_side.personal_experiment.scalping_strategy import build_prompt

class V14Tests(unittest.TestCase):
    def test_independent_starting_state(self):
        s = scalping_v14.initial_state()
        self.assertEqual(s["cash"], 5000)
        self.assertEqual(s["positions"], {})
        self.assertEqual(scalping_v14.CONFIG["version"], "V1.4")
        self.assertEqual(scalping_v14.CONFIG["max_trades_per_day"], 2)

    def test_prompt_has_correct_capital_and_rules(self):
        now = datetime(2026,11,23,10,0,tzinfo=ZoneInfo("America/New_York"))
        prompt = build_prompt(scalping_v14.initial_state(), [], now, scalping_v14.CONFIG, "Kallisto V1.4")
        self.assertIn("Starting capital: $5,000.00 USD", prompt)
        self.assertIn("V1.4: maximum two distinct entries", prompt)
        self.assertNotIn("Starting capital: $1,000 USD", prompt)

    def test_fee_aware_breakeven_is_opt_in(self):
        now = datetime(2026,11,23,10,30,tzinfo=ZoneInfo("America/New_York"))
        def position():
            return {"side":"LONG", "entry_price":100., "stop_price":99.,
                    "initial_stop_price":99., "target_price":104.,
                    "opened_at":datetime(2026,11,23,10,0,tzinfo=now.tzinfo).isoformat(),
                    "shares":10, "breakeven_armed":False}
        bar={"high":101.5,"low":100.5,"close":101.2}
        control=position()
        trial=position()
        self.assertIsNone(evaluate_bar(control,bar,now,{"version":"V1.3","max_hold_minutes":60}))
        self.assertIsNone(evaluate_bar(trial,bar,now,scalping_v14.CONFIG))
        self.assertEqual(control["stop_price"],100.)
        self.assertGreater(trial["stop_price"],100.)

if __name__ == "__main__":
    unittest.main()
