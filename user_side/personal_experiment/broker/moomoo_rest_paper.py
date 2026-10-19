"""Azure-native Moomoo paper broker.

The adapter uses Moomoo's REST simulated-trading endpoints and never exposes a
real-money order path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from user_side.personal_experiment.broker.moomoo_policy import is_new_position_allowed
from user_side.personal_experiment.broker.moomoo_rest import MoomooRestClient
from user_side.personal_experiment.broker.safety import BrokerSafetyGate, BrokerSafetyState, OrderIntent


US_SIM_MARKET_ID = 2
ACTIVE_ORDER_STATUSES = {2, 3}


@dataclass(frozen=True)
class RestBrokerSnapshot:
    account_id: str
    cash: float
    total_assets: float
    positions: dict[str, float]
    open_orders: dict[str, dict]


class MoomooRestPaperBroker:
    mode = "MOOMOO_REST_PAPER"

    def __init__(
        self,
        client: MoomooRestClient,
        *,
        account_id: str | None = None,
        market_id: int = US_SIM_MARKET_ID,
        gate: BrokerSafetyGate | None = None,
    ) -> None:
        self.client = client
        self.market_id = int(market_id)
        self._account_id = (account_id or "").strip() or None
        self.gate = gate or BrokerSafetyGate(live_trading_enabled=False)
        self.safety_state = BrokerSafetyState()

    @classmethod
    def from_env(cls) -> "MoomooRestPaperBroker":
        return cls(
            MoomooRestClient.from_env(),
            account_id=os.environ.get("MOOMOO_PAPER_ACCOUNT_ID"),
            market_id=int(os.environ.get("MOOMOO_PAPER_MARKET_ID", str(US_SIM_MARKET_ID))),
        )

    def account_id(self) -> str:
        if self._account_id:
            return self._account_id
        accounts = self.client.simulated_accounts()
        for account in accounts:
            if int(account.get("market_id", -1)) == self.market_id:
                self._account_id = str(account["account_id"])
                return self._account_id
        raise RuntimeError(
            f"No Moomoo simulated account found for market_id={self.market_id}. "
            "Open the paper account in Moomoo first or set MOOMOO_PAPER_ACCOUNT_ID."
        )

    def snapshot(self) -> RestBrokerSnapshot:
        acc_id = self.account_id()
        cash_info = self.client.cash_info(acc_id)
        positions_raw = self.client.positions(acc_id)
        orders_raw = self.client.orders(acc_id)

        positions: dict[str, float] = {}
        for row in positions_raw:
            qty = float(row.get("qty") or 0.0)
            if not qty:
                continue
            symbol = str(row.get("symbol") or "").upper().strip()
            direction = int(row.get("pstn_type") or 0)
            positions[symbol] = -abs(qty) if direction == 1 else abs(qty)

        open_orders = {
            str(row.get("order_id")): row
            for row in orders_raw
            if int(row.get("status") or 0) in ACTIVE_ORDER_STATUSES
        }
        return RestBrokerSnapshot(
            account_id=acc_id,
            cash=float(cash_info.get("balance") or 0.0),
            total_assets=float(cash_info.get("total_asset") or cash_info.get("balance") or 0.0),
            positions=positions,
            open_orders=open_orders,
        )

    def find_order_by_remark(self, remark: str) -> dict | None:
        for order in self.client.orders(self.account_id()):
            if str(order.get("text") or "") == remark:
                return order
        return None

    def short_available(self, ticker: str, qty: int) -> bool:
        info = self.client.max_buy_sell(
            self.account_id(),
            symbol=ticker.upper().strip(),
            order_type=3,
        )
        return float(info.get("max_sell_short_qty") or 0) >= int(qty)

    def preflight_entry(
        self,
        *,
        intent: OrderIntent,
        quote_time,
        now,
        session_start_equity: float,
        current_equity: float,
    ):
        manually_blocked = not is_new_position_allowed(intent.ticker)
        shortable = None
        if intent.side.upper().strip() == "SHORT":
            shortable = self.short_available(intent.ticker, intent.qty)
        return self.gate.preflight(
            environment="SIMULATE",
            intent=intent,
            state=self.safety_state,
            quote_time=quote_time,
            now=now,
            session_start_equity=session_start_equity,
            current_equity=current_equity,
            broker_shortable=shortable,
            manually_blocked=manually_blocked,
        )

    @staticmethod
    def _open_side(side: str) -> int:
        return 1 if side.upper().strip() == "LONG" else 3

    @staticmethod
    def _close_side(side: str) -> int:
        return 2 if side.upper().strip() == "LONG" else 4

    def submit_market_entry(
        self,
        *,
        intent: OrderIntent,
        quote_time,
        now,
        session_start_equity: float,
        current_equity: float,
        remark: str,
    ) -> dict:
        existing = self.find_order_by_remark(remark)
        if existing is not None:
            return {"submitted": False, "duplicate": True, "existing_order": existing}

        decision = self.preflight_entry(
            intent=intent,
            quote_time=quote_time,
            now=now,
            session_start_equity=session_start_equity,
            current_equity=current_equity,
        )
        if not decision.allowed:
            return {"submitted": False, "reason": decision.reason}

        result = self.client.place_order(
            self.account_id(),
            market=self.market_id,
            symbol=intent.ticker.upper().strip(),
            order_side=self._open_side(intent.side),
            qty=int(intent.qty),
            order_type=3,
            text=remark,
        )
        self.gate.mark_submitted(intent, self.safety_state)
        return {"submitted": True, "result": result}

    def submit_market_close(
        self,
        *,
        ticker: str,
        original_side: str,
        qty: int,
        remark: str,
    ) -> dict:
        existing = self.find_order_by_remark(remark)
        if existing is not None:
            return {"submitted": False, "duplicate": True, "existing_order": existing}
        result = self.client.place_order(
            self.account_id(),
            market=self.market_id,
            symbol=ticker.upper().strip(),
            order_side=self._close_side(original_side),
            qty=int(qty),
            order_type=3,
            text=remark,
        )
        return {"submitted": True, "result": result}

    def cancel_open_orders(self) -> list[dict]:
        out = []
        for order_id in self.snapshot().open_orders:
            out.append(self.client.cancel_order(self.account_id(), order_id))
        return out
