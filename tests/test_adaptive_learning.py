import unittest

from user_side.personal_experiment.adaptive_learning import BOUNDS, DEFAULT_CONFIG, _bounded_config, _next_version


class AdaptiveLearningTests(unittest.TestCase):
    def test_version_increment(self):
        self.assertEqual(_next_version("V1.0"), "V1.1")
        self.assertEqual(_next_version("V1.9"), "V1.10")

    def test_evaluator_cannot_escape_risk_bounds(self):
        proposal = {
            "changes": {
                "risk_per_trade_pct": 0.50,
                "max_open_positions": 99,
                "min_confidence": 0.01,
                "max_hold_minutes": 999,
            },
            "learning_notes": "Prefer evidence-backed setups only.",
        }
        bounded = _bounded_config(dict(DEFAULT_CONFIG), proposal)
        self.assertEqual(bounded["risk_per_trade_pct"], BOUNDS["risk_per_trade_pct"][1])
        self.assertEqual(bounded["max_open_positions"], 3)
        self.assertEqual(bounded["min_confidence"], 0.55)
        self.assertEqual(bounded["max_hold_minutes"], 90)

    def test_unknown_parameters_are_ignored(self):
        proposal = {"changes": {"disable_daily_loss_limit": 1, "risk_per_trade_pct": 0.004}}
        bounded = _bounded_config(dict(DEFAULT_CONFIG), proposal)
        self.assertNotIn("disable_daily_loss_limit", bounded)
        self.assertEqual(bounded["risk_per_trade_pct"], 0.004)


if __name__ == "__main__":
    unittest.main()
