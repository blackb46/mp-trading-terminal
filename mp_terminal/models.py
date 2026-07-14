"""Core data models shared across scanners and the scoring engine."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Recommendation(str, Enum):
    BUY = "Buy"
    HOLD = "Hold"
    AVOID = "Avoid"


class RiskLevel(str, Enum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"


class Quote(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    prev_close: Optional[float] = None
    day_open: Optional[float] = None
    vwap: Optional[float] = None
    volume: Optional[int] = None
    avg_volume_30d: Optional[int] = None
    float_shares: Optional[int] = None
    day_low: Optional[float] = None
    day_high: Optional[float] = None
    avg_day_high: Optional[float] = None
    avg_day_low: Optional[float] = None
    avg_5d_low: Optional[float] = None

    @property
    def daily_change_pct(self) -> Optional[float]:
        if self.prev_close and self.prev_close > 0:
            return (self.price - self.prev_close) / self.prev_close * 100
        return None

    @property
    def rvol(self) -> Optional[float]:
        if self.avg_volume_30d and self.avg_volume_30d > 0 and self.volume is not None:
            return self.volume / self.avg_volume_30d
        return None

    @property
    def gap_pct(self) -> Optional[float]:
        """Open vs previous close — a proxy for premarket move (no true premarket feed)."""
        if self.day_open and self.prev_close and self.prev_close > 0:
            return (self.day_open - self.prev_close) / self.prev_close * 100
        return None

    @property
    def range_pct(self) -> Optional[float]:
        """Day high-low as a percent of price — a same-day volatility proxy."""
        if self.day_high is not None and self.day_low is not None and self.price:
            return (self.day_high - self.day_low) / self.price * 100
        return None

    @property
    def range_position(self) -> Optional[float]:
        """Where the last price sits in the day's range: 0 (at low) .. 1 (at high)."""
        if self.day_high is not None and self.day_low is not None and self.day_high > self.day_low:
            return (self.price - self.day_low) / (self.day_high - self.day_low)
        return None


class CategoryScores(BaseModel):
    # Schwab-only (trimmed) scope — see docs/SCOPE.md. News/Sentiment/Institutional cut.
    technical: float = 0.0     # weight 35%
    momentum: float = 0.0      # weight 28%
    volume: float = 0.0        # weight 22%
    premarket: float = 0.0     # weight 8%
    risk: float = 0.0          # weight 7%


class ScoredStock(BaseModel):
    quote: Quote
    company_name: Optional[str] = None
    overall_score: float = 0.0
    ai_confidence: float = 0.0
    recommendation: Recommendation = Recommendation.HOLD
    risk_level: RiskLevel = RiskLevel.MODERATE
    scores: CategoryScores = CategoryScores()
