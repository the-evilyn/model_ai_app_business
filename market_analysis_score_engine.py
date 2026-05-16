from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any
import math
import re


MARKET_WEIGHTS = {
    "market_size": 0.25,
    "growth_rate": 0.25,
    "competition": 0.20,
    "traction": 0.15,
    "trend": 0.10,
    "geographic_fit": 0.05,
}

SECTOR_RISK_DEFAULTS = {
    "AI": {"trend": 82, "competition": 68},
    "SaaS": {"trend": 76, "competition": 72},
    "Fintech": {"trend": 73, "competition": 78},
    "Health": {"trend": 70, "competition": 62},
    "Ecommerce": {"trend": 66, "competition": 84},
    "Climate": {"trend": 80, "competition": 58},
    "Crypto": {"trend": 55, "competition": 80},
    "Real Estate": {"trend": 62, "competition": 70},
    "Education": {"trend": 67, "competition": 60},
    "Food": {"trend": 60, "competition": 75},
    "Other": {"trend": 55, "competition": 65},
}

SECTOR_ALIASES = {
    "ai": "AI",
    "artificial intelligence": "AI",
    "machine learning": "AI",
    "software": "SaaS",
    "saas": "SaaS",
    "fintech": "Fintech",
    "finance": "Fintech",
    "health": "Health",
    "sante": "Health",
    "santé": "Health",
    "medical": "Health",
    "ecommerce": "Ecommerce",
    "e-commerce": "Ecommerce",
    "commerce": "Ecommerce",
    "retail": "Ecommerce",
    "climate": "Climate",
    "green": "Climate",
    "energy": "Climate",
    "crypto": "Crypto",
    "blockchain": "Crypto",
    "real estate": "Real Estate",
    "immobilier": "Real Estate",
    "house": "Real Estate",
    "houses": "Real Estate",
    "education": "Education",
    "school": "Education",
    "food": "Food",
    "restaurant": "Food",
    "painting": "Other",
    "art": "Other",
}

COUNTRY_BUSINESS_FIT = {
    "morocco": 66,
    "maroc": 66,
    "france": 74,
    "usa": 82,
    "united states": 82,
    "canada": 78,
    "spain": 72,
    "germany": 80,
    "uk": 79,
}


@dataclass
class MarketAnalysisRequest:
    sector: str
    market_size_billion: float | None = None
    market_growth_rate_percent: float | None = None
    competition_level: str | float | None = None
    product_traction_users: int | None = None
    search_trend_score: float | None = None
    country: str | None = None
    region: str | None = None
    notes: str | None = None


@dataclass
class MarketAnalysisResult:
    market_score: float
    market_label: str
    confidence_score: float
    normalized_sector: str
    sub_scores: dict[str, float]
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class MarketAnalysisScoreEngine:
    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = self._normalize_weights(weights or MARKET_WEIGHTS)

    def analyze(self, request: MarketAnalysisRequest | dict[str, Any]) -> MarketAnalysisResult:
        if isinstance(request, dict):
            allowed_fields = {item.name for item in fields(MarketAnalysisRequest)}
            request = MarketAnalysisRequest(**{key: value for key, value in request.items() if key in allowed_fields})

        normalized_sector = self.normalize_sector(request.sector, request.notes or "")
        defaults = SECTOR_RISK_DEFAULTS.get(normalized_sector, SECTOR_RISK_DEFAULTS["Other"])

        warnings: list[str] = []
        if normalized_sector == "Other":
            warnings.append("Sector is not mapped to a known market category. Score confidence is reduced.")

        market_size_score = self._market_size_score(request.market_size_billion)
        growth_score = self._growth_score(request.market_growth_rate_percent)
        competition_score = self._competition_score(request.competition_level, defaults["competition"])
        traction_score = self._traction_score(request.product_traction_users)
        trend_score = self._trend_score(request.search_trend_score, defaults["trend"])
        geographic_score = self._geographic_fit_score(request.country, request.region)

        sub_scores = {
            "market_size": market_size_score,
            "growth_rate": growth_score,
            "competition": competition_score,
            "traction": traction_score,
            "trend": trend_score,
            "geographic_fit": geographic_score,
        }

        score = sum(self.weights[key] * sub_scores[key] for key in self.weights)
        confidence = self._confidence(request, normalized_sector)

        return MarketAnalysisResult(
            market_score=round(self._bounded(score), 2),
            market_label=self.label(score),
            confidence_score=round(confidence, 2),
            normalized_sector=normalized_sector,
            sub_scores={key: round(value, 2) for key, value in sub_scores.items()},
            warnings=warnings,
            details={
                "weights": self.weights,
                "input": asdict(request),
                "defaults_used_for_sector": defaults,
            },
        )

    def normalize_sector(self, sector: str, notes: str = "") -> str:
        text = self._clean_text(f"{sector} {notes}")
        sector_only = self._clean_text(sector)

        for alias, canonical in SECTOR_ALIASES.items():
            if alias == sector_only:
                return canonical

        for alias, canonical in SECTOR_ALIASES.items():
            if alias in text:
                return canonical

        return "Other"

    @staticmethod
    def label(score: float) -> str:
        if score >= 75:
            return "Very attractive market"
        if score >= 60:
            return "Promising market"
        if score >= 45:
            return "Moderate / needs validation"
        return "Weak market opportunity"

    def _market_size_score(self, value: float | None) -> float:
        if value is None:
            return 55.0
        return self._normalize_log(value, low=0.05, high=250.0)

    def _growth_score(self, value: float | None) -> float:
        if value is None:
            return 55.0
        return self._bounded((float(value) + 5) / 35 * 100)

    def _competition_score(self, value: str | float | None, default_competition: float) -> float:
        if value is None:
            competition_risk = default_competition
        elif isinstance(value, (int, float)):
            competition_risk = self._bounded(float(value))
        else:
            mapping = {
                "low": 25,
                "faible": 25,
                "medium": 50,
                "moyen": 50,
                "high": 80,
                "eleve": 80,
                "elevé": 80,
            }
            competition_risk = mapping.get(self._clean_text(value), default_competition)
        return 100 - competition_risk

    def _traction_score(self, value: int | None) -> float:
        if value is None:
            return 50.0
        return self._normalize_log(max(int(value), 0) + 1, low=1, high=2_000_000)

    def _trend_score(self, value: float | None, default_trend: float) -> float:
        if value is None:
            return self._bounded(default_trend)
        return self._bounded(float(value))

    def _geographic_fit_score(self, country: str | None, region: str | None) -> float:
        if not country and not region:
            return 55.0
        text = self._clean_text(f"{country or ''} {region or ''}")
        for key, score in COUNTRY_BUSINESS_FIT.items():
            if key in text:
                return float(score)
        return 60.0

    def _confidence(self, request: MarketAnalysisRequest, normalized_sector: str) -> float:
        fields = [
            request.sector,
            request.market_size_billion,
            request.market_growth_rate_percent,
            request.competition_level,
            request.product_traction_users,
            request.search_trend_score,
            request.country,
        ]
        completeness = sum(value not in [None, ""] for value in fields) / len(fields)
        sector_factor = 0.75 if normalized_sector == "Other" else 1.0
        return self._bounded(100 * (0.35 + 0.65 * completeness) * sector_factor)

    @staticmethod
    def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
        total = sum(max(float(value), 0.0) for value in weights.values())
        if total <= 0:
            return MARKET_WEIGHTS.copy()
        return {key: max(float(value), 0.0) / total for key, value in weights.items()}

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", str(value).lower().strip())

    @staticmethod
    def _bounded(value: float, low: float = 0.0, high: float = 100.0) -> float:
        if math.isnan(value) or math.isinf(value):
            return 50.0
        return max(low, min(high, float(value)))

    def _normalize_log(self, value: float, low: float, high: float) -> float:
        value = max(float(value), low)
        low_log = math.log1p(low)
        high_log = math.log1p(high)
        value_log = math.log1p(value)
        return self._bounded((value_log - low_log) / (high_log - low_log) * 100)


def score_market(payload: dict[str, Any]) -> dict[str, Any]:
    engine = MarketAnalysisScoreEngine()
    return asdict(engine.analyze(payload))


if __name__ == "__main__":
    example = {
        "sector": "immobilier",
        "market_size_billion": 25,
        "market_growth_rate_percent": 7,
        "competition_level": "high",
        "product_traction_users": 12000,
        "search_trend_score": 68,
        "country": "Morocco",
        "notes": "Marketplace for houses and real estate comparison.",
    }
    print(score_market(example))
