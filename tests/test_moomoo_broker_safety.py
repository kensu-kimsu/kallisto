from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from user_side.personal_experiment.broker.safety import (
    BrokerSafetyGate,
    BrokerSafetyState,
    OrderIntent,
)


class BrokerSafetyTests(unittest.TestCase):
    def setUp(self):
        self.gate = BrokerSafetyGate(
            max_quote_age_seconds=30,
            daily_loss_limit_pct=0.02,
            live_trading_enabled=False,
        )
        self.state = BrokerSafetyState()
        self.now = datetime.now(timezone.utc)
        self.intent = OrderIntent(
            ticker="AAPL",
            side="LONG",
            qty=1,
            limit_price=250.0,
            session_date="2026-10-16",
            strategy_version="V1.0",
        )

    def test_live_trading_is_hard_disabled(self):
        result = self.gate.require_paper_environment("REAL")
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "LIVE_TRADING_HARD_DISABLED")

    def test_stale_quote_blocks_order(self):
        result = self.gate.quote_is_fresh(self.now - timedelta(seconds=31), self.now)
        self.assertFalse(result.allowed)
        self.assertTrue(result.reason.startswith("STALE_QUOTE"))

    def test_daily_loss_limit_blocks_order(self):
        result = self.gate.check_daily_loss(
            session_start_equity=1000.0,
            current_equity=979.0,
        )
        self.assertFalse(result.allowed)
        self.assertTrue(result.reason.startswith("DAILY_LOSS_LOCK"))

    def test_duplicate_intent_is_blocked_after_submission(self):
        first = self.gate.check_duplicate(self.intent, self.state)
        self.assertTrue(first.allowed)
        self.gate.mark_submitted(self.intent, self.state)
        second = self.gate.check_duplicate(self.intent, self.state)
        self.assertFalse(second.allowed)
        self.assertTrue(second.reason.startswith("DUPLICATE_ORDER_INTENT"))

    def test_short_requires_explicit_broker_confirmation(self):
        short = self.gate.check_short_eligibility(
            side="SHORT",
            broker_shortable=None,
            manually_blocked=False,
        )
        self.assertFalse(short.allowed)
        self.assertEqual(short.reason, "SHORT_NOT_VERIFIED_AVAILABLE")

    def test_reconciliation_failure_blocks_preflight(self):
        self.state.reconciliation_ok = False
        result = self.gate.preflight(
            environment="SIMULATE",
            intent=self.intent,
            state=self.state,
            quote_time=self.now,
            now=self.now,
            session_start_equity=1000.0,
            current_equity=1000.0,
            broker_shortable=True,
            manually_blocked=False,
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "BROKER_RECONCILIATION_FAILED")


if __name__ == "__main__":
    unittest.main()
