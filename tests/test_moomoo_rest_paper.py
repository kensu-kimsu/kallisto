from __future__ import annotations

import unittest
from datetime import datetime, timezone

from user_side.personal_experiment.broker.moomoo_rest import build_signing_string
from user_side.personal_experiment.broker.moomoo_rest_paper import MoomooRestPaperBroker
from user_side.personal_experiment.broker.moomoo_shadow import _event_key
from user_side.personal_experiment.broker.safety import BrokerSafetyGate, BrokerSafetyState, OrderIntent


class MoomooRestPaperTests(unittest.TestCase):
    def test_signing_string_keeps_empty_fields(self):
        value = build_signing_string(
            1782357937000,
            "GET",
            "/api/v1.0/quote/trading-days",
            "market=HK&start=2025-12-22&end=2025-12-26",
            b"",
        )
        self.assertEqual(
            value,
            "1782357937000\nGET\n/api/v1.0/quote/trading-days\n"
            "market=HK&start=2025-12-22&end=2025-12-26\n",
        )

    def test_rest_paper_side_mapping(self):
        self.assertEqual(MoomooRestPaperBroker._open_side("LONG"), 1)
        self.assertEqual(MoomooRestPaperBroker._open_side("SHORT"), 3)
        self.assertEqual(MoomooRestPaperBroker._close_side("LONG"), 2)
        self.assertEqual(MoomooRestPaperBroker._close_side("SHORT"), 4)

    def test_source_event_key_is_deterministic(self):
        a = _event_key("2026-10-19T10:00:00-04:00", "OPEN", "NVDA", "LONG", 2)
        b = _event_key("2026-10-19T10:00:00-04:00", "OPEN", "NVDA", "LONG", 2)
        c = _event_key("2026-10-19T10:00:00-04:00", "CLOSE", "NVDA", "LONG", 2)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_live_environment_remains_hard_blocked(self):
        gate = BrokerSafetyGate(live_trading_enabled=False)
        self.assertFalse(gate.require_paper_environment("REAL").allowed)

    def test_stale_quote_blocks_entry(self):
        gate = BrokerSafetyGate(max_quote_age_seconds=30, live_trading_enabled=False)
        state = BrokerSafetyState()
        intent = OrderIntent(
            ticker="NVDA",
            side="LONG",
            qty=1,
            limit_price=100.0,
            session_date="2026-10-19",
            strategy_version="V1.0",
        )
        now = datetime(2026, 10, 19, 15, 0, 40, tzinfo=timezone.utc)
        quote = datetime(2026, 10, 19, 15, 0, 0, tzinfo=timezone.utc)
        result = gate.preflight(
            environment="SIMULATE",
            intent=intent,
            state=state,
            quote_time=quote,
            now=now,
            session_start_equity=1000.0,
            current_equity=1000.0,
            broker_shortable=None,
            manually_blocked=False,
        )
        self.assertFalse(result.allowed)
        self.assertTrue(result.reason.startswith("STALE_QUOTE:"))


if __name__ == "__main__":
    unittest.main()
