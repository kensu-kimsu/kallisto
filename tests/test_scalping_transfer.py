from __future__ import annotations

import unittest
from datetime import datetime, timezone

from user_side.personal_experiment.scalping_interfaces import (
    SimulationExecutionGateway,
    YFinanceMarketDataProvider,
)


class TransferContractTests(unittest.TestCase):
    def test_market_data_contract_methods_exist(self):
        provider = YFinanceMarketDataProvider()
        for name in ("scan_premarket", "technical_snapshot", "session_bars", "latest_price"):
            self.assertTrue(callable(getattr(provider, name, None)))

    def test_execution_contract_methods_exist(self):
        gateway = SimulationExecutionGateway()
        self.assertEqual(gateway.mode, "SIMULATION")
        for name in ("mark_to_market", "open_trade", "close_trade", "evaluate_bar"):
            self.assertTrue(callable(getattr(gateway, name, None)))

    def test_simulation_gateway_preserves_no_leverage_cash_reservation(self):
        gateway = SimulationExecutionGateway()
        state = {
            "cash": 1000.0,
            "positions": {},
            "session_start_equity": 1000.0,
            "high_water_mark": 1000.0,
            "paused": False,
        }
        candidate = {
            "ticker": "TEST",
            "universe": "titan",
            "technical": {"price": 100.0, "atr_pct": 0.005},
        }
        proposal = {
            "ticker": "TEST",
            "side": "LONG",
            "target_pct": 0.01,
            "confidence": 0.8,
            "rationale": "test",
        }
        before = state["cash"]
        pos = gateway.open_trade(
            state=state,
            proposal=proposal,
            candidate=candidate,
            now_et=datetime.now(timezone.utc),
            current_equity=1000.0,
        )
        self.assertIsNotNone(pos)
        self.assertLess(state["cash"], before)
        self.assertGreaterEqual(state["cash"], 150.0)


if __name__ == "__main__":
    unittest.main()
