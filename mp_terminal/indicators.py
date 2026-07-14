"""Technical indicators — pure functions over lists of OHLCV bars.

No external dependencies, fully deterministic, so they're easy to unit-test. A "bar" is a
dict with float keys o, h, l, c, v (open/high/low/close/volume), oldest-first.

Implements the indicators from Paul's spec that are computable from historical price bars:
EMA (9/20/200) + alignment, MACD, RSI, VWAP, ATR, ADR, and average volume (for RVOL).
"""
from __future__ import annotations

from typing import Optional


def sma(values: list[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema_series(values: list[float], period: int) -> list[float]:
    """EMA as a series, seeded with the SMA of the first `period` values."""
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    e = sum(values[:period]) / period
    out = [e]
    for v in values[period:]:
        e = v * k + e * (1 - k)
        out.append(e)
    return out


def ema(values: list[float], period: int) -> Optional[float]:
    s = ema_series(values, period)
    return s[-1] if s else None


def rsi(closes: list[float], period: int = 14) -> Optional[float]:
    """Wilder's RSI."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9):
    """Return (macd_line, signal_line, histogram) for the latest bar, or None."""
    if len(closes) < slow + signal:
        return None
    ema_fast = ema_series(closes, fast)
    ema_slow = ema_series(closes, slow)
    diff = len(ema_fast) - len(ema_slow)  # fast series is longer; align tails
    ema_fast = ema_fast[diff:]
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = ema_series(macd_line, signal)
    d2 = len(macd_line) - len(signal_line)
    macd_aligned = macd_line[d2:]
    hist = macd_aligned[-1] - signal_line[-1]
    return macd_aligned[-1], signal_line[-1], hist


def atr(bars: list[dict], period: int = 14) -> Optional[float]:
    """Average True Range (Wilder)."""
    if len(bars) < period + 1:
        return None
    trs = []
    for i in range(1, len(bars)):
        h, l, pc = bars[i]["h"], bars[i]["l"], bars[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    a = sum(trs[:period]) / period
    for tr in trs[period:]:
        a = (a * (period - 1) + tr) / period
    return a


def adr(bars: list[dict], period: int = 20) -> Optional[float]:
    """Average Daily Range (absolute) over the last `period` bars."""
    if len(bars) < period:
        return None
    recent = bars[-period:]
    return sum(b["h"] - b["l"] for b in recent) / period


def vwap_from_bars(bars: list[dict]) -> Optional[float]:
    """Volume-weighted average price over the provided bars (typical price)."""
    num = den = 0.0
    for b in bars:
        tp = (b["h"] + b["l"] + b["c"]) / 3
        vol = b.get("v") or 0
        num += tp * vol
        den += vol
    return num / den if den else None


def ema_alignment(closes: list[float]) -> str:
    """9/20/200 EMA stack -> 'bullish' | 'bearish' | 'neutral'.

    Falls back to a 50-period EMA when there isn't enough history for the 200.
    """
    e9, e20 = ema(closes, 9), ema(closes, 20)
    e_long = ema(closes, 200) or ema(closes, 50)
    if None in (e9, e20, e_long):
        return "neutral"
    if e9 > e20 > e_long:
        return "bullish"
    if e9 < e20 < e_long:
        return "bearish"
    return "neutral"


def analyze(bars: list[dict]) -> dict:
    """Compute the full indicator set from historical bars. Returns None-valued keys when
    there isn't enough history rather than raising, so callers can display gracefully."""
    closes = [b["c"] for b in bars]
    m = macd(closes)
    return {
        "ema9": ema(closes, 9),
        "ema20": ema(closes, 20),
        "ema200": ema(closes, 200),
        "alignment": ema_alignment(closes),
        "rsi": rsi(closes),
        "macd_line": m[0] if m else None,
        "macd_signal": m[1] if m else None,
        "macd_hist": m[2] if m else None,
        "atr": atr(bars),
        "adr": adr(bars),
        "vwap": vwap_from_bars(bars[-1:]) if bars else None,  # latest-bar typical price
        "avg_vol_20": sma([float(b.get("v") or 0) for b in bars], 20),
        "last_close": closes[-1] if closes else None,
    }
