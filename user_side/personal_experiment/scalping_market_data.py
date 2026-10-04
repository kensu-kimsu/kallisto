"""Market-data helpers for the simulation-only scalping experiment."""

from __future__ import annotations

from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

from user_side.personal_experiment.market_data.microcap_screener import (
    get_microcap_universe,
)
from user_side.personal_experiment.market_data.titan_screener import (
    get_titan_universe,
)

NY = ZoneInfo("America/New_York")


def intraday(ticker: str, period: str = "2d") -> pd.DataFrame:
    frame = yf.Ticker(ticker).history(
        period=period,
        interval="5m",
        prepost=True,
        auto_adjust=False,
    )
    if frame.empty:
        return frame
    if frame.index.tz is None:
        frame.index = frame.index.tz_localize("UTC").tz_convert(NY)
    else:
        frame.index = frame.index.tz_convert(NY)
    return frame.rename(columns={c: str(c).lower() for c in frame.columns})


def session_bars(ticker: str, day) -> pd.DataFrame:
    frame = intraday(ticker)
    if frame.empty:
        return frame
    frame = frame.loc[frame.index.date == day]
    if frame.empty:
        return frame
    return frame.between_time("09:30", "16:00")


def premarket_stats(ticker: str, day) -> dict | None:
    frame = intraday(ticker)
    if frame.empty:
        return None
    day_frame = frame.loc[frame.index.date == day]
    if day_frame.empty:
        return None
    pre = day_frame.between_time("04:00", "09:29")
    if pre.empty:
        return None

    volume = float(pre["volume"].fillna(0).sum())
    if volume <= 0:
        return None
    first = float(pre["open"].dropna().iloc[0])
    last = float(pre["close"].dropna().iloc[-1])
    return {
        "premarket_volume": int(volume),
        "premarket_price": round(last, 4),
        "premarket_change_pct": round(((last / first) - 1) * 100, 3) if first else 0.0,
    }


def scan_premarket(day, leaders_per_universe: int = 5) -> list[dict]:
    groups = [
        ("microcap", get_microcap_universe(candidate_count=50)),
        ("titan", get_titan_universe(top_n=20)),
    ]
    leaders: list[dict] = []

    for universe, frame in groups:
        rows = []
        for item in frame.to_dict("records"):
            ticker = str(item.get("ticker", "")).upper().strip()
            if not ticker:
                continue
            stats = premarket_stats(ticker, day)
            if stats is None:
                continue
            rows.append({
                "ticker": ticker,
                "name": item.get("name", ticker),
                "universe": universe,
                "market_cap": item.get("market_cap"),
                "avg_volume": item.get("avg_volume", item.get("volume", 0)),
                **stats,
            })
        rows.sort(key=lambda x: x["premarket_volume"], reverse=True)
        leaders.extend(rows[:leaders_per_universe])

    # Fundamental fields are context only; the intraday signals remain primary.
    for item in leaders:
        try:
            info = yf.Ticker(item["ticker"]).info
        except Exception:
            info = {}
        item["fundamental"] = {
            key: info.get(key)
            for key in (
                "marketCap", "floatShares", "averageVolume", "beta",
                "trailingPE", "forwardPE", "priceToBook", "profitMargins",
                "revenueGrowth", "earningsGrowth", "returnOnEquity",
                "debtToEquity", "shortPercentOfFloat",
            )
            if info.get(key) is not None
        }
    return leaders


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(frame: pd.DataFrame, window: int = 14) -> pd.Series:
    prev = frame["close"].shift(1)
    tr = pd.concat([
        frame["high"] - frame["low"],
        (frame["high"] - prev).abs(),
        (frame["low"] - prev).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def technical_snapshot(ticker: str, day) -> dict | None:
    bars = session_bars(ticker, day)
    if bars.empty or len(bars) < 3:
        return None

    close = bars["close"].astype(float)
    volume = bars["volume"].fillna(0).astype(float)
    typical = (bars["high"] + bars["low"] + bars["close"]) / 3
    vwap = (typical * volume).cumsum() / volume.cumsum().replace(0, np.nan)
    ema9 = _ema(close, 9)
    ema20 = _ema(close, 20)
    macd = _ema(close, 12) - _ema(close, 26)
    macd_signal = _ema(macd, 9)
    rsi14 = _rsi(close)
    atr14 = _atr(bars)

    first30 = bars.between_time("09:30", "09:59")
    opening_high = float(first30["high"].max()) if not first30.empty else float(bars["high"].iloc[0])
    opening_low = float(first30["low"].min()) if not first30.empty else float(bars["low"].iloc[0])
    price = float(close.iloc[-1])
    atr_value = (
        float(atr14.dropna().iloc[-1])
        if not atr14.dropna().empty
        else float((bars["high"] - bars["low"]).mean())
    )
    recent_volume = float(volume.tail(min(6, len(volume))).mean())
    base_volume = float(volume.mean()) or 1.0

    return {
        "timestamp_et": bars.index[-1].isoformat(),
        "price": round(price, 4),
        "vwap": round(float(vwap.iloc[-1]), 4),
        "ema9": round(float(ema9.iloc[-1]), 4),
        "ema20": round(float(ema20.iloc[-1]), 4),
        "rsi14": round(float(rsi14.dropna().iloc[-1]), 2) if not rsi14.dropna().empty else None,
        "macd": round(float(macd.iloc[-1]), 5),
        "macd_signal": round(float(macd_signal.iloc[-1]), 5),
        "atr_pct": round(atr_value / price, 5) if price > 0 else 0.0,
        "relative_volume": round(recent_volume / base_volume, 3),
        "opening_range_high": round(opening_high, 4),
        "opening_range_low": round(opening_low, 4),
        "above_vwap": bool(price > float(vwap.iloc[-1])),
        "ema_bullish": bool(float(ema9.iloc[-1]) > float(ema20.iloc[-1])),
        "opening_breakout": bool(price > opening_high),
        "opening_breakdown": bool(price < opening_low),
    }


def latest_price(ticker: str, day) -> float | None:
    bars = session_bars(ticker, day)
    if bars.empty:
        return None
    return float(bars["close"].iloc[-1])
