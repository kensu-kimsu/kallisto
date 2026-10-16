from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Iterable


@dataclass(frozen=True)
class OrderIntent:
    ticker: str
    side: str
    qty: int
    limit_price: float
    session_date: str
    strategy_version: str
    reason: str = "ENTRY"

    def key(self) -> str:
        raw = "|".join(
            [
                self.session_date,
                self.ticker.upper().strip(),
                self.side.upper().strip(),
                str(int(self.qty)),
                f"{float(self.limit_price):.6f}",
                self.strategy_version,
                self.reason,
            ]
        )
        return sha256(raw.encode("utf-8")).hexdigest()[:24]


@dataclass
class BrokerSafetyState:
    seen_intents: set[str] = field(default_factory=set)
    daily_locked: bool = False
    reconciliation_ok: bool = True
    stale_data: bool = False
    last_error: str = ""


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    reason: str


class BrokerSafetyGate:
    """Deterministic guardrails that the LLM cannot bypass."""

    def __init__(
        self,
        *,
        max_quote_age_seconds: int = 30,
        daily_loss_limit_pct: float = 0.02,
        live_trading_enabled: bool = False,
    ) -> None:
        self.max_quote_age = timedelta(seconds=max_quote_age_seconds)
        self.daily_loss_limit_pct = float(daily_loss_limit_pct)
        self.live_trading_enabled = bool(live_trading_enabled)

    def require_paper_environment(self, environment: str) -> SafetyDecision:
        env = environment.upper().strip()
        if env == "REAL" and not self.live_trading_enabled:
            return SafetyDecision(False, "LIVE_TRADING_HARD_DISABLED")
        if env != "SIMULATE":
            return SafetyDecision(False, f"UNSUPPORTED_ENVIRONMENT:{env}")
        return SafetyDecision(True, "PAPER_ENVIRONMENT_OK")

    def quote_is_fresh(self, quote_time: datetime, now: datetime) -> SafetyDecision:
        age = now - quote_time
        if age.total_seconds() < 0:
            return SafetyDecision(False, "QUOTE_TIMESTAMP_IN_FUTURE")
        if age > self.max_quote_age:
            return SafetyDecision(False, f"STALE_QUOTE:{int(age.total_seconds())}s")
        return SafetyDecision(True, "QUOTE_FRESH")

    def check_daily_loss(
        self,
        *,
        session_start_equity: float,
        current_equity: float,
    ) -> SafetyDecision:
        if session_start_equity <= 0:
            return SafetyDecision(False, "INVALID_SESSION_START_EQUITY")
        loss_pct = max(0.0, (session_start_equity - current_equity) / session_start_equity)
        if loss_pct >= self.daily_loss_limit_pct:
            return SafetyDecision(False, f"DAILY_LOSS_LOCK:{loss_pct:.4%}")
        return SafetyDecision(True, "DAILY_LOSS_OK")

    def check_duplicate(self, intent: OrderIntent, state: BrokerSafetyState) -> SafetyDecision:
        key = intent.key()
        if key in state.seen_intents:
            return SafetyDecision(False, f"DUPLICATE_ORDER_INTENT:{key}")
        return SafetyDecision(True, f"NEW_ORDER_INTENT:{key}")

    def mark_submitted(self, intent: OrderIntent, state: BrokerSafetyState) -> str:
        key = intent.key()
        state.seen_intents.add(key)
        return key

    def check_reconciliation(self, state: BrokerSafetyState) -> SafetyDecision:
        if not state.reconciliation_ok:
            return SafetyDecision(False, "BROKER_RECONCILIATION_FAILED")
        return SafetyDecision(True, "BROKER_RECONCILIATION_OK")

    def check_short_eligibility(
        self,
        *,
        side: str,
        broker_shortable: bool | None,
        manually_blocked: bool,
    ) -> SafetyDecision:
        if manually_blocked:
            return SafetyDecision(False, "SYMBOL_BLOCKED_FOR_NEW_POSITION")
        if side.upper().strip() != "SHORT":
            return SafetyDecision(True, "LONG_ELIGIBLE")
        if broker_shortable is not True:
            return SafetyDecision(False, "SHORT_NOT_VERIFIED_AVAILABLE")
        return SafetyDecision(True, "SHORT_ELIGIBLE")

    def preflight(
        self,
        *,
        environment: str,
        intent: OrderIntent,
        state: BrokerSafetyState,
        quote_time: datetime,
        now: datetime,
        session_start_equity: float,
        current_equity: float,
        broker_shortable: bool | None,
        manually_blocked: bool,
    ) -> SafetyDecision:
        checks: Iterable[SafetyDecision] = (
            self.require_paper_environment(environment),
            self.check_reconciliation(state),
            self.quote_is_fresh(quote_time, now),
            self.check_daily_loss(
                session_start_equity=session_start_equity,
                current_equity=current_equity,
            ),
            self.check_duplicate(intent, state),
            self.check_short_eligibility(
                side=intent.side,
                broker_shortable=broker_shortable,
                manually_blocked=manually_blocked,
            ),
        )
        for check in checks:
            if not check.allowed:
                return check
        return SafetyDecision(True, "PREFLIGHT_OK")
