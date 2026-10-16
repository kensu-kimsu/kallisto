from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from user_side.personal_experiment.broker.moomoo_policy import is_new_position_allowed
from user_side.personal_experiment.broker.safety import (
    BrokerSafetyGate,
    BrokerSafetyState,
    OrderIntent,
    SafetyDecision,
)


@dataclass(frozen=True)
class BrokerSnapshot:
    cash: float
    total_assets: float
    positions: dict[str, float]
    open_orders: dict[str, dict]


class MoomooPaperBroker:
    """Moomoo OpenAPI paper-trading adapter.

    Live trading is intentionally unsupported here. This class always uses
    TrdEnv.SIMULATE and exists so Kallisto can validate real broker state,
    order lifecycle, fills, duplicate protection and reconciliation before any
    future live branch is considered.
    """

    mode = "MOOMOO_PAPER"

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 11111,
        acc_id: int = 0,
        gate: BrokerSafetyGate | None = None,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.acc_id = int(acc_id)
        self.gate = gate or BrokerSafetyGate(live_trading_enabled=False)
        self.safety_state = BrokerSafetyState()
        self._ctx = None
        self._api: dict[str, Any] | None = None

    def _load_api(self) -> dict[str, Any]:
        if self._api is not None:
            return self._api
        try:
            from moomoo import (  # type: ignore
                ModifyOrderOp,
                OpenSecTradeContext,
                OrderType,
                RET_OK,
                SecurityFirm,
                TrdEnv,
                TrdMarket,
                TrdSide,
            )
        except ImportError as exc:
            raise RuntimeError(
                "Moomoo OpenAPI Python SDK is not installed. Install it only on the paper-trading host."
            ) from exc
        self._api = {
            "ModifyOrderOp": ModifyOrderOp,
            "OpenSecTradeContext": OpenSecTradeContext,
            "OrderType": OrderType,
            "RET_OK": RET_OK,
            "SecurityFirm": SecurityFirm,
            "TrdEnv": TrdEnv,
            "TrdMarket": TrdMarket,
            "TrdSide": TrdSide,
        }
        return self._api

    def connect(self) -> None:
        if self._ctx is not None:
            return
        api = self._load_api()
        self._ctx = api["OpenSecTradeContext"](
            filter_trdmarket=api["TrdMarket"].US,
            host=self.host,
            port=self.port,
            security_firm=api["SecurityFirm"].FUTUINC,
        )

    def close(self) -> None:
        if self._ctx is not None:
            self._ctx.close()
            self._ctx = None

    def _require_ctx(self):
        if self._ctx is None:
            self.connect()
        return self._ctx

    def snapshot(self) -> BrokerSnapshot:
        api = self._load_api()
        ctx = self._require_ctx()
        trd_env = api["TrdEnv"].SIMULATE

        ret, account = ctx.accinfo_query(trd_env=trd_env, acc_id=self.acc_id)
        if ret != api["RET_OK"] or account.empty:
            raise RuntimeError(f"Moomoo paper account query failed: {account}")
        row = account.iloc[0]
        cash = float(row.get("cash", 0.0))
        total_assets = float(row.get("total_assets", row.get("total_assets_val", cash)))

        ret, pos = ctx.position_list_query(trd_env=trd_env, acc_id=self.acc_id)
        if ret != api["RET_OK"]:
            raise RuntimeError(f"Moomoo paper position query failed: {pos}")
        positions: dict[str, float] = {}
        if not pos.empty:
            for _, r in pos.iterrows():
                qty = float(r.get("qty", 0.0))
                if qty:
                    positions[str(r.get("code", ""))] = qty

        ret, orders = ctx.order_list_query(trd_env=trd_env, acc_id=self.acc_id, refresh_cache=True)
        if ret != api["RET_OK"]:
            raise RuntimeError(f"Moomoo paper order query failed: {orders}")
        open_orders: dict[str, dict] = {}
        if not orders.empty:
            terminal = {"FILLED_ALL", "CANCELLED_ALL", "FAILED", "DISABLED", "DELETED"}
            for _, r in orders.iterrows():
                status = str(r.get("order_status", ""))
                if status not in terminal:
                    open_orders[str(r.get("order_id", ""))] = r.to_dict()

        return BrokerSnapshot(
            cash=cash,
            total_assets=total_assets,
            positions=positions,
            open_orders=open_orders,
        )

    def get_order_state(self, order_id: str) -> dict:
        api = self._load_api()
        ctx = self._require_ctx()
        ret, data = ctx.order_list_query(
            order_id=str(order_id),
            trd_env=api["TrdEnv"].SIMULATE,
            acc_id=self.acc_id,
            refresh_cache=True,
        )
        if ret != api["RET_OK"] or data.empty:
            return {"found": False, "order_id": str(order_id), "error": str(data)}
        row = data.iloc[0]
        requested = float(row.get("qty", 0.0) or 0.0)
        dealt = float(row.get("dealt_qty", 0.0) or 0.0)
        return {
            "found": True,
            "order_id": str(row.get("order_id", order_id)),
            "status": str(row.get("order_status", "")),
            "requested_qty": requested,
            "dealt_qty": dealt,
            "remaining_qty": max(0.0, requested - dealt),
            "dealt_avg_price": float(row.get("dealt_avg_price", 0.0) or 0.0),
            "partial_fill": dealt > 0 and dealt < requested,
            "code": str(row.get("code", "")),
        }

    def cancel_order(self, order_id: str) -> dict:
        api = self._load_api()
        ctx = self._require_ctx()
        ret, data = ctx.modify_order(
            api["ModifyOrderOp"].CANCEL,
            str(order_id),
            0,
            0,
            trd_env=api["TrdEnv"].SIMULATE,
            acc_id=self.acc_id,
        )
        return {
            "cancel_requested": ret == api["RET_OK"],
            "order_id": str(order_id),
            "broker_response": str(data),
        }

    def cancel_open_orders(self) -> list[dict]:
        snap = self.snapshot()
        return [self.cancel_order(order_id) for order_id in snap.open_orders]

    def reconcile(self, expected_positions: dict[str, float]) -> SafetyDecision:
        snap = self.snapshot()
        normalized_expected = {
            str(k).upper().strip(): float(v)
            for k, v in expected_positions.items()
            if abs(float(v)) > 1e-9
        }
        normalized_broker = {
            str(k).upper().strip(): float(v)
            for k, v in snap.positions.items()
            if abs(float(v)) > 1e-9
        }
        ok = normalized_expected == normalized_broker
        self.safety_state.reconciliation_ok = ok
        if ok:
            return SafetyDecision(True, "BROKER_RECONCILIATION_OK")
        return SafetyDecision(
            False,
            f"BROKER_RECONCILIATION_FAILED expected={normalized_expected} actual={normalized_broker}",
        )

    def submit_limit_order(
        self,
        *,
        intent: OrderIntent,
        quote_time,
        now,
        session_start_equity: float,
        current_equity: float,
        broker_shortable: bool | None,
    ) -> dict:
        manually_blocked = not is_new_position_allowed(intent.ticker)
        decision = self.gate.preflight(
            environment="SIMULATE",
            intent=intent,
            state=self.safety_state,
            quote_time=quote_time,
            now=now,
            session_start_equity=session_start_equity,
            current_equity=current_equity,
            broker_shortable=broker_shortable,
            manually_blocked=manually_blocked,
        )
        if not decision.allowed:
            return {"submitted": False, "reason": decision.reason, "intent_key": intent.key()}

        api = self._load_api()
        ctx = self._require_ctx()
        side = intent.side.upper().strip()
        trd_side = api["TrdSide"].BUY if side == "LONG" else api["TrdSide"].SELL
        code = intent.ticker if "." in intent.ticker else f"US.{intent.ticker.upper()}"

        ret, data = ctx.place_order(
            price=float(intent.limit_price),
            qty=int(intent.qty),
            code=code,
            trd_side=trd_side,
            order_type=api["OrderType"].NORMAL,
            trd_env=api["TrdEnv"].SIMULATE,
            acc_id=self.acc_id,
            remark=f"Kallisto:{intent.key()}",
        )
        if ret != api["RET_OK"]:
            return {
                "submitted": False,
                "reason": f"BROKER_REJECTED:{data}",
                "intent_key": intent.key(),
            }

        key = self.gate.mark_submitted(intent, self.safety_state)
        first = data.iloc[0].to_dict() if hasattr(data, "iloc") and not data.empty else {}
        return {
            "submitted": True,
            "intent_key": key,
            "order_id": str(first.get("order_id", "")),
            "order_status": str(first.get("order_status", "")),
            "requested_qty": int(intent.qty),
            "dealt_qty": float(first.get("dealt_qty", 0.0) or 0.0),
            "dealt_avg_price": float(first.get("dealt_avg_price", 0.0) or 0.0),
        }

    def flatten_position(self, code: str, qty: float, limit_price: float) -> dict:
        """Submit a paper reduce order for an existing broker position.

        This deliberately does not infer direction from strategy state; it uses
        the sign of the broker-reported quantity as the source of truth.
        """
        api = self._load_api()
        ctx = self._require_ctx()
        side = api["TrdSide"].SELL if qty > 0 else api["TrdSide"].BUY
        ret, data = ctx.place_order(
            price=float(limit_price),
            qty=int(abs(qty)),
            code=str(code),
            trd_side=side,
            order_type=api["OrderType"].NORMAL,
            trd_env=api["TrdEnv"].SIMULATE,
            acc_id=self.acc_id,
            remark="Kallisto:EOD_FLATTEN",
        )
        first = data.iloc[0].to_dict() if ret == api["RET_OK"] and hasattr(data, "iloc") and not data.empty else {}
        return {
            "submitted": ret == api["RET_OK"],
            "code": str(code),
            "qty": abs(float(qty)),
            "order_id": str(first.get("order_id", "")),
            "broker_response": str(data),
        }

    def verify_flat(self) -> SafetyDecision:
        snap = self.snapshot()
        if snap.positions:
            return SafetyDecision(False, f"EOD_NOT_FLAT:{snap.positions}")
        return SafetyDecision(True, "EOD_FLAT_CONFIRMED")
