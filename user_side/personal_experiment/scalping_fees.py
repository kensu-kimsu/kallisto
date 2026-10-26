"""Moomoo Australia fee model for Kallisto P/L reporting.

This module does not change Kallisto's simulated fill engine. It converts the
existing gross trade log into broker-fee-adjusted results so headline P/L,
equity and return reporting reflects the intended Moomoo Australia cost model.

Fee schedule source checked 2026-10-26:
- Commission: USD 0
- Platform fee: USD 0.99 per order
- Settlement fee: USD 0.003/share, capped at 1% of transaction amount
- SEC fee: sells only, USD 0.0000206 * transaction amount, minimum USD 0.01/trade
- FINRA TAF: sells only, USD 0.000195/share, minimum USD 0.01/trade, maximum USD 9.79/trade
- CAT fee: NMS stocks USD 0.000003/share

ADR custody fees and stock-borrow fees are security/account specific and cannot
be inferred from the current trade log. They can be supplied explicitly when
known; otherwise they are reported as zero rather than invented.
"""

from __future__ import annotations

from dataclasses import dataclass

PLATFORM_FEE_PER_ORDER = 0.99
SETTLEMENT_FEE_PER_SHARE = 0.003
SETTLEMENT_FEE_CAP_PCT = 0.01
SEC_FEE_RATE = 0.0000206
SEC_FEE_MIN = 0.01
CAT_FEE_PER_SHARE_NMS = 0.000003
TAF_FEE_PER_SHARE = 0.000195
TAF_FEE_MIN = 0.01
TAF_FEE_MAX = 9.79


@dataclass(frozen=True)
class FeeBreakdown:
    platform_fee: float
    settlement_fee: float
    sec_fee: float
    taf_fee: float
    cat_fee: float
    adr_fee: float = 0.0
    borrow_fee: float = 0.0

    @property
    def total(self) -> float:
        return (
            self.platform_fee
            + self.settlement_fee
            + self.sec_fee
            + self.taf_fee
            + self.cat_fee
            + self.adr_fee
            + self.borrow_fee
        )

    def as_dict(self) -> dict:
        return {
            "platform_fee": self.platform_fee,
            "settlement_fee": self.settlement_fee,
            "sec_fee": self.sec_fee,
            "taf_fee": self.taf_fee,
            "cat_fee": self.cat_fee,
            "adr_fee": self.adr_fee,
            "borrow_fee": self.borrow_fee,
            "total_fee": self.total,
        }


def order_fees(
    *,
    shares: int,
    price: float,
    is_sell: bool,
    adr_fee_per_share: float = 0.0,
    borrow_fee: float = 0.0,
) -> FeeBreakdown:
    shares = max(0, int(shares))
    price = max(0.0, float(price))
    amount = shares * price

    settlement = min(
        SETTLEMENT_FEE_PER_SHARE * shares,
        SETTLEMENT_FEE_CAP_PCT * amount,
    )
    sec = max(SEC_FEE_MIN, SEC_FEE_RATE * amount) if is_sell and amount > 0 else 0.0
    taf = min(TAF_FEE_MAX, max(TAF_FEE_MIN, TAF_FEE_PER_SHARE * shares)) if is_sell and shares > 0 else 0.0
    cat = CAT_FEE_PER_SHARE_NMS * shares
    adr = max(0.0, float(adr_fee_per_share)) * shares

    return FeeBreakdown(
        platform_fee=PLATFORM_FEE_PER_ORDER if shares > 0 else 0.0,
        settlement_fee=settlement,
        sec_fee=sec,
        taf_fee=taf,
        cat_fee=cat,
        adr_fee=adr,
        borrow_fee=max(0.0, float(borrow_fee)),
    )


def round_trip_fees(
    *,
    side: str,
    shares: int,
    entry_price: float,
    exit_price: float,
    adr_fee_per_share: float = 0.0,
    borrow_fee: float = 0.0,
) -> dict:
    side = str(side).upper().strip()
    short = side == "SHORT"

    entry = order_fees(
        shares=shares,
        price=entry_price,
        is_sell=short,
        adr_fee_per_share=0.0,
        borrow_fee=borrow_fee if short else 0.0,
    )
    exit_leg = order_fees(
        shares=shares,
        price=exit_price,
        is_sell=not short,
        adr_fee_per_share=adr_fee_per_share,
        borrow_fee=0.0,
    )

    total = entry.total + exit_leg.total
    return {
        "entry": entry.as_dict(),
        "exit": exit_leg.as_dict(),
        "total_fee": total,
    }


def fee_adjusted_trade(trade: dict) -> dict:
    shares = int(float(trade.get("shares") or 0))
    entry_price = float(trade.get("entry_price") or 0.0)
    exit_price = float(trade.get("exit_price") or 0.0)
    gross_pnl = float(trade.get("gross_pnl_usd") or trade.get("pnl_usd") or 0.0)

    fees = round_trip_fees(
        side=trade.get("side", "LONG"),
        shares=shares,
        entry_price=entry_price,
        exit_price=exit_price,
        adr_fee_per_share=float(trade.get("adr_fee_per_share") or 0.0),
        borrow_fee=float(trade.get("borrow_fee_usd") or 0.0),
    )
    total_fees = float(fees["total_fee"])
    net_pnl = gross_pnl - total_fees

    row = dict(trade)
    row["gross_pnl_usd"] = round(gross_pnl, 4)
    row["fees_usd"] = round(total_fees, 4)
    row["net_pnl_usd"] = round(net_pnl, 4)
    row["fee_breakdown"] = fees
    return row
