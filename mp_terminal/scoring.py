"""Weighted AI recommendation scoring engine (Schwab-only scope).

Combines per-category sub-scores (each 0-100) into an overall 0-100 score, then derives a
Buy/Hold/Avoid recommendation and a Low/Moderate/High risk level. Sub-scores themselves are
produced by the analysis layer (technical, momentum, ...) — stubbed for now.
"""
from __future__ import annotations

from mp_terminal.models import CategoryScores, Recommendation, RiskLevel, ScoredStock

# Weights must sum to 1.0. News/Sentiment/Institutional were cut (no Schwab source) and their
# combined 30% redistributed proportionally across the remaining categories. See docs/SCOPE.md.
WEIGHTS = {
    "technical": 0.35,
    "momentum": 0.28,
    "volume": 0.22,
    "premarket": 0.08,
    "risk": 0.07,
}


def overall_score(scores: CategoryScores) -> float:
    return round(sum(getattr(scores, cat) * w for cat, w in WEIGHTS.items()), 1)


def recommendation_for(score: float) -> Recommendation:
    if score >= 70:
        return Recommendation.BUY
    if score >= 45:
        return Recommendation.HOLD
    return Recommendation.AVOID


def risk_level_for(scores: CategoryScores) -> RiskLevel:
    # Higher `risk` sub-score = safer. Invert to a risk level.
    if scores.risk >= 66:
        return RiskLevel.LOW
    if scores.risk >= 33:
        return RiskLevel.MODERATE
    return RiskLevel.HIGH


def finalize(stock: ScoredStock) -> ScoredStock:
    """Populate overall score, recommendation, and risk level from sub-scores."""
    stock.overall_score = overall_score(stock.scores)
    stock.recommendation = recommendation_for(stock.overall_score)
    stock.risk_level = risk_level_for(stock.scores)
    return stock
