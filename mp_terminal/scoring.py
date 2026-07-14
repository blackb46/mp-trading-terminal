"""AI recommendation scoring engine.

Two paths, both producing real (non-placeholder) 0-100 sub-scores:

  - compute_basic_scores(quote): uses only fields available for the whole market without extra
    API calls (change %, gap %, day range, range position, volume). Used to rank the scanners
    and recommendation cards fast, within free-tier rate limits.

  - compute_full_scores(quote, analysis): folds in the real technical indicators (EMA
    alignment, RSI, MACD, ATR, RVOL) computed from historical bars. Used on the Stock Detail
    view, where we fetch bars for the single selected symbol.

Sub-scores are combined with the configured weights into an overall 0-100 score. See
docs/SCOPE.md for why News/Sentiment/Institutional were dropped (no data source).
"""
from __future__ import annotations

from typing import Optional

from mp_terminal.models import CategoryScores, Quote, Recommendation, RiskLevel, ScoredStock

WEIGHTS = {
    "technical": 0.35,
    "momentum": 0.28,
    "volume": 0.22,
    "premarket": 0.08,
    "risk": 0.07,
}


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


# ------------------------------- basic (whole-market, no extra calls) -------------------------------
def compute_basic_scores(q: Quote) -> CategoryScores:
    change = q.daily_change_pct or 0.0
    pos = q.range_position                     # 0..1, where price sits in the day range
    gap = q.gap_pct
    rng = q.range_pct

    # Technical: closing strong within the day's range is constructive.
    technical = 45.0
    if pos is not None:
        technical = 30 + pos * 55              # near high -> ~85, near low -> ~30
    # Momentum: today's directional move.
    momentum = _clamp(50 + change * 3)         # +10% -> 80, -10% -> 20
    # Volume: without an average we can't do true RVOL here; use a magnitude proxy.
    volume = 40.0
    if q.volume:
        volume = _clamp(35 + (q.volume / 1_000_000) * 4)  # more volume -> higher, capped
    # Premarket: gap up is bullish for this strategy (proxy — no true premarket feed).
    premarket = 50.0
    if gap is not None:
        premarket = _clamp(50 + gap * 5)
    # Risk sub-score: higher = safer. Wide daily range = riskier.
    risk = 60.0
    if rng is not None:
        risk = _clamp(85 - rng * 3)            # 5% range -> 70, 15% range -> 40
    return CategoryScores(technical=technical, momentum=momentum, volume=volume,
                          premarket=premarket, risk=risk)


# ------------------------------- full (uses real indicators from bars) -------------------------------
def _rsi_score(rsi: Optional[float]) -> float:
    if rsi is None:
        return 50.0
    if rsi >= 70:
        return 62.0        # overbought — momentum yes, but extended
    if rsi >= 55:
        return 88.0        # strong, healthy uptrend
    if rsi >= 45:
        return 60.0
    if rsi >= 30:
        return 40.0
    return 28.0            # oversold


def compute_full_scores(q: Quote, analysis: dict) -> CategoryScores:
    price = analysis.get("last_close") or q.price
    align = analysis.get("alignment", "neutral")
    ema20 = analysis.get("ema20")
    rsi = analysis.get("rsi")
    hist = analysis.get("macd_hist")
    atr = analysis.get("atr")
    avg_vol = analysis.get("avg_vol_20")

    # Technical: EMA stack alignment, nudged by price vs the 20 EMA.
    technical = {"bullish": 82, "neutral": 50, "bearish": 24}.get(align, 50)
    if ema20 and price:
        technical += 8 if price > ema20 else -8
    technical = _clamp(technical)

    # Momentum: RSI regime + MACD histogram sign.
    momentum = _rsi_score(rsi)
    if hist is not None:
        momentum += 8 if hist > 0 else -8
    momentum = _clamp(momentum)

    # Volume: real RVOL against the 20-day average.
    volume = 45.0
    if avg_vol and q.volume:
        rvol = q.volume / avg_vol
        volume = _clamp(35 + min(rvol, 6) * 10)   # RVOL 5x -> 85, 1x -> 45
    # Premarket: gap proxy (no true premarket feed).
    premarket = _clamp(50 + (q.gap_pct or 0) * 5)
    # Risk: ATR as a percent of price — lower volatility scores safer.
    risk = 60.0
    if atr and price:
        atr_pct = atr / price * 100
        risk = _clamp(85 - atr_pct * 6)           # 3% ATR -> 67, 8% ATR -> 37
    return CategoryScores(technical=technical, momentum=momentum, volume=volume,
                          premarket=premarket, risk=risk)


# ------------------------------- combine -------------------------------
def overall_score(scores: CategoryScores) -> float:
    return round(sum(getattr(scores, cat) * w for cat, w in WEIGHTS.items()), 1)


def recommendation_for(score: float) -> Recommendation:
    if score >= 68:
        return Recommendation.BUY
    if score >= 45:
        return Recommendation.HOLD
    return Recommendation.AVOID


def risk_level_for(scores: CategoryScores) -> RiskLevel:
    if scores.risk >= 66:
        return RiskLevel.LOW
    if scores.risk >= 40:
        return RiskLevel.MODERATE
    return RiskLevel.HIGH


def finalize(stock: ScoredStock) -> ScoredStock:
    stock.overall_score = overall_score(stock.scores)
    stock.ai_confidence = stock.overall_score
    stock.recommendation = recommendation_for(stock.overall_score)
    stock.risk_level = risk_level_for(stock.scores)
    return stock


def score_quote(q: Quote, analysis: Optional[dict] = None) -> ScoredStock:
    scores = compute_full_scores(q, analysis) if analysis else compute_basic_scores(q)
    return finalize(ScoredStock(quote=q, company_name=q.company_name, scores=scores))
