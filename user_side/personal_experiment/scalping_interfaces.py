"""Broker-neutral interfaces for Final V1.

Final V1 remains simulation-only. These adapters isolate strategy/risk logic from
market-data and execution backends so a future moomoo AU paper/live adapter can
replace the simulation backend without rewriting the LLM decision engine.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import pandas as pd

from user_side.personal_experiment import scalping_engine
from user_side.personal_experiment import scalping_market_data


class MarketDataProvider(Protocol):
    def scan_premarket(self, day, leaders_per_universe: int) -> list[dict]: ...
    def technical_snapshot(self, ticker: str, day) -> dict | None: ...
    def session_bars(self, ticker: str, day) -> pd.DataFrame: ...
    def latest_price(self, ticker: str, day) -> float | None: ...


class ExecutionGateway(Protocol):
    mode: str

    def mark_to_market(self, state: dict, prices: dict[str, float]) -> float: ...

    def open_trade(
        self,
        *,
        state: dict,
        proposal: dict,
        candidate: dict,
        now_et: datetime,
        current_equity: float,
    ) -> dict | None: ...

    def close_trade(
        self,
        *,
        state: dict,
        ticker: str,
        exit_price: float,
        reason: str,
        now_et: datetime,
    ) -> dict: ...

    def evaluate_bar(
        self,
        pos: dict,
        bar,
        bar_time: datetime | None = None,
    ) -> tuple[float, str] | None: ...


class YFinanceMarketDataProvider:
    """Current public-data backend used by Final V1."""

    name = "yfinance-public-5m"

    def scan_premarket(self, day, leaders_per_universe: int) -> list[dict]:
        return scalping_market_data.scan_premarket(day, leaders_per_universe)

    def technical_snapshot(self, ticker: str, day) -> dict | None:
        return scalping_market_data.technical_snapshot(ticker, day)

    def session_bars(self, ticker: str, day) -> pd.DataFrame:
        return scalping_market_data.session_bars(ticker, day)

    def latest_price(self, ticker: str, day) -> float | None:
        return scalping_market_data.latest_price(ticker, day)


class SimulationExecutionGateway:
    """Current deterministic hypothetical-fill backend.

    The future moomoo adapter should implement the same responsibilities while
    replacing synthetic fills with broker order submission, order-state events,
    fills, account/position reconciliation, and broker-side buying-power checks.
    """

    mode = "SIMULATION"

    def mark_to_market(self, state: dict, prices: dict[str, float]) -> float:
        return scalping_engine.mark_to_market(state, prices)

    def open_trade(
        self,
        *,
        state: dict,
        proposal: dict,
        candidate: dict,
        now_et: datetime,
        current_equity: float,
    ) -> dict | None:
        return scalping_engine.open_simulated_trade(
            state=state,
            proposal=proposal,
            candidate=candidate,
            now_et=now_et,
            current_equity=current_equity,
        )

    def close_trade(
        self,
        *,
        state: dict,
        ticker: str,
        exit_price: float,
        reason: str,
        now_et: datetime,
    ) -> dict:
        return scalping_engine.close_simulated_trade(
            state=state,
            ticker=ticker,
            exit_price=exit_price,
            reason=reason,
            now_et=now_et,
        )

    def evaluate_bar(
        self,
        pos: dict,
        bar,
        bar_time: datetime | None = None,
    ) -> tuple[float, str] | None:
        return scalping_engine.evaluate_bar(pos, bar, bar_time)


MARKET_DATA: MarketDataProvider = YFinanceMarketDataProvider()
EXECUTION: ExecutionGateway = SimulationExecutionGateway()
