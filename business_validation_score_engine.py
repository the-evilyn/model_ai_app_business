from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import math
import re

try:
    from market_analysis_score_engine import MarketAnalysisScoreEngine
except Exception:
    MarketAnalysisScoreEngine = None


DEFAULT_WEIGHTS = {
    "startup_success": 0.40,
    "market_sentiment": 0.25,
    "market_analysis": 0.20,
    "specialist_or_risk": 0.15,
}

STARTUP_MODEL_SECTORS = {
    "AI",
    "Climate",
    "Crypto",
    "Ecommerce",
    "Fintech",
    "Health",
    "SaaS",
}

SECTOR_KEYWORDS = {
    "AI": [
        "ai",
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "automation",
        "chatbot",
        "computer vision",
    ],
    "SaaS": [
        "saas",
        "software",
        "crm",
        "erp",
        "subscription",
        "b2b software",
        "cloud",
    ],
    "Fintech": [
        "fintech",
        "finance",
        "bank",
        "payment",
        "insurance",
        "investment",
        "accounting",
        "loan",
    ],
    "Health": [
        "health",
        "medical",
        "doctor",
        "clinic",
        "hospital",
        "pharmacy",
        "wellness",
        "fitness",
    ],
    "Ecommerce": [
        "ecommerce",
        "e-commerce",
        "retail",
        "shop",
        "store",
        "marketplace",
        "selling",
        "commerce",
    ],
    "Climate": [
        "climate",
        "green",
        "energy",
        "solar",
        "sustainability",
        "recycling",
        "environment",
    ],
    "Crypto": [
        "crypto",
        "blockchain",
        "web3",
        "token",
        "wallet",
        "nft",
    ],
}

GENERAL_SECTOR_MAP = {
    "real estate": "Other",
    "immobilier": "Other",
    "houses": "Other",
    "housing": "Other",
    "construction": "Other",
    "painting": "Other",
    "art": "Other",
    "restaurant": "Other",
    "food": "Other",
    "education": "Other",
    "agriculture": "Other",
    "transport": "Other",
}

POSITIVE_WORDS = {
    "love",
    "good",
    "great",
    "excellent",
    "amazing",
    "useful",
    "demand",
    "growing",
    "positive",
    "recommend",
    "like",
    "best",
    "fast",
    "easy",
    "valuable",
}

NEGATIVE_WORDS = {
    "bad",
    "poor",
    "expensive",
    "complain",
    "hate",
    "slow",
    "uncertain",
    "problem",
    "difficult",
    "negative",
    "risk",
    "weak",
    "fail",
    "failure",
    "low",
}


@dataclass
class BusinessValidationRequest:
    project_name: str
    project_description: str
    sector: str
    funding_rounds: int = 1
    founder_experience_years: float = 0.0
    team_size: int = 1
    market_size_billion: float = 1.0
    product_traction_users: int = 0
    burn_rate_million: float = 0.0
    revenue_million: float = 0.000001
    investor_type: str = "none"
    founder_background: str = "first_time"
    market_growth_rate_percent: float | None = None
    competition_level: str | float | None = None
    search_trend_score: float | None = None
    country: str | None = None
    region: str | None = None
    specialist_match_score: float | None = None
    risk_score: float | None = None
    opinions: list[str] = field(default_factory=list)


@dataclass
class BusinessValidationResult:
    final_score: float
    final_label: str
    confidence_score: float
    startup_success_score: float
    market_sentiment_score: float
    market_analysis_score: float
    specialist_or_risk_score: float
    original_sector: str
    normalized_sector: str
    startup_model_sector: str
    sector_reliability: float
    warnings: list[str]
    details: dict[str, Any]


class BusinessValidationScoreEngine:
    def __init__(
        self,
        startup_model_path: str | Path = "artifacts/startup_success_binary_best_model.joblib",
        sentiment_model_path: str | Path = "artifacts/sentiment_analysis_pipeline.joblib",
        weights: dict[str, float] | None = None,
    ) -> None:
        self.startup_model_path = Path(startup_model_path)
        self.sentiment_model_path = Path(sentiment_model_path)
        self.weights = self._normalize_weights(weights or DEFAULT_WEIGHTS)
        self.startup_artifact = self._load_joblib(self.startup_model_path)
        self.sentiment_artifact = self._load_joblib(self.sentiment_model_path)

    def validate(self, request: BusinessValidationRequest | dict[str, Any]) -> BusinessValidationResult:
        if isinstance(request, dict):
            request = BusinessValidationRequest(**request)

        sector_info = self.normalize_sector(request.sector, request.project_description)
        warnings: list[str] = []

        if sector_info["startup_model_sector"] == "Other":
            warnings.append(
                "Sector not present in the startup dataset. Startup score is still computed, "
                "but sector confidence is reduced."
            )

        startup_score = self.startup_success_score(request, sector_info["startup_model_sector"])
        sentiment_score = self.market_sentiment_score(request.opinions or [request.project_description])
        market_score = self.market_analysis_score(request)
        specialist_score = self.specialist_or_risk_score(request)

        raw_final = (
            self.weights["startup_success"] * startup_score
            + self.weights["market_sentiment"] * sentiment_score
            + self.weights["market_analysis"] * market_score
            + self.weights["specialist_or_risk"] * specialist_score
        )

        confidence = self._bounded(
            100
            * (
                0.55
                + 0.25 * sector_info["sector_reliability"]
                + 0.10 * min(len(request.opinions), 5) / 5
                + 0.10 * self._structured_data_completeness(request)
            )
        )

        final_score = self._bounded(raw_final * (0.85 + 0.15 * sector_info["sector_reliability"]))
        final_label = self.score_label(final_score)

        return BusinessValidationResult(
            final_score=round(final_score, 2),
            final_label=final_label,
            confidence_score=round(confidence, 2),
            startup_success_score=round(startup_score, 2),
            market_sentiment_score=round(sentiment_score, 2),
            market_analysis_score=round(market_score, 2),
            specialist_or_risk_score=round(specialist_score, 2),
            original_sector=request.sector,
            normalized_sector=sector_info["normalized_sector"],
            startup_model_sector=sector_info["startup_model_sector"],
            sector_reliability=round(sector_info["sector_reliability"], 2),
            warnings=warnings,
            details={
                "weights": self.weights,
                "startup_model_loaded": self.startup_artifact is not None,
                "sentiment_model_loaded": self.sentiment_artifact is not None,
                "input": asdict(request),
            },
        )

    def normalize_sector(self, sector: str, description: str = "") -> dict[str, Any]:
        text = f"{sector} {description}".lower()
        normalized = self._clean_text(sector)

        for known_sector in STARTUP_MODEL_SECTORS:
            if self._clean_text(known_sector) == normalized:
                return {
                    "normalized_sector": known_sector,
                    "startup_model_sector": known_sector,
                    "sector_reliability": 1.0,
                }

        for keyword, mapped_sector in GENERAL_SECTOR_MAP.items():
            if keyword in normalized:
                return {
                    "normalized_sector": keyword.title(),
                    "startup_model_sector": mapped_sector,
                    "sector_reliability": 0.65,
                }

        for model_sector, keywords in SECTOR_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                return {
                    "normalized_sector": model_sector,
                    "startup_model_sector": model_sector,
                    "sector_reliability": 0.85,
                }

        return {
            "normalized_sector": sector.strip() or "Unknown",
            "startup_model_sector": "Other",
            "sector_reliability": 0.55,
        }

    def startup_success_score(self, request: BusinessValidationRequest, startup_model_sector: str) -> float:
        pipeline = self._extract_pipeline(self.startup_artifact)
        if pipeline is None:
            return self._heuristic_startup_score(request)

        feature_order = self._artifact_value("train_columns_after_filtering", DEFAULT_STARTUP_FEATURES)
        input_df = self._prepare_startup_input(request, startup_model_sector, feature_order)

        try:
            if hasattr(pipeline, "predict_proba"):
                probabilities = pipeline.predict_proba(input_df)[0]
                classes = self._pipeline_classes(pipeline)
                positive_index = self._positive_class_index(classes)
                return float(probabilities[positive_index] * 100)
            prediction = pipeline.predict(input_df)[0]
            return 75.0 if self._is_positive_prediction(prediction) else 35.0
        except Exception:
            return self._heuristic_startup_score(request)

    def market_sentiment_score(self, opinions: list[str]) -> float:
        clean_opinions = [opinion for opinion in opinions if str(opinion).strip()]
        if not clean_opinions:
            return 50.0

        pipeline = self._extract_pipeline(self.sentiment_artifact)
        if pipeline is None:
            return self._keyword_sentiment_score(clean_opinions)

        try:
            if hasattr(pipeline, "predict_proba"):
                probabilities = pipeline.predict_proba(clean_opinions)[:, 1]
                return float(probabilities.mean() * 100)
            predictions = pipeline.predict(clean_opinions)
            return float(sum(predictions) / len(predictions) * 100)
        except Exception:
            return self._keyword_sentiment_score(clean_opinions)

    def market_analysis_score(self, request: BusinessValidationRequest) -> float:
        if MarketAnalysisScoreEngine is not None:
            try:
                result = MarketAnalysisScoreEngine().analyze(
                    {
                        "sector": request.sector,
                        "market_size_billion": request.market_size_billion,
                        "market_growth_rate_percent": request.market_growth_rate_percent,
                        "competition_level": request.competition_level,
                        "product_traction_users": request.product_traction_users,
                        "search_trend_score": request.search_trend_score,
                        "country": request.country,
                        "region": request.region,
                        "notes": request.project_description,
                    }
                )
                return result.market_score
            except Exception:
                pass

        size_score = self._normalize_positive(request.market_size_billion, low=0.2, high=80.0)

        if request.market_growth_rate_percent is None:
            growth_score = 55.0
        else:
            growth_score = self._normalize_positive(request.market_growth_rate_percent, low=-5.0, high=25.0)

        competition_score = self._competition_to_score(request.competition_level)
        traction_score = self._normalize_positive(request.product_traction_users, low=0, high=1_000_000)

        return self._bounded(
            0.35 * size_score
            + 0.30 * growth_score
            + 0.20 * competition_score
            + 0.15 * traction_score
        )

    def specialist_or_risk_score(self, request: BusinessValidationRequest) -> float:
        if request.specialist_match_score is not None:
            specialist_score = self._bounded(float(request.specialist_match_score))
        else:
            specialist_score = 55.0

        if request.risk_score is not None:
            risk_adjusted_score = 100.0 - self._bounded(float(request.risk_score))
        else:
            risk_adjusted_score = 55.0

        return self._bounded(0.60 * specialist_score + 0.40 * risk_adjusted_score)

    @staticmethod
    def score_label(score: float) -> str:
        if score >= 75:
            return "Strong validation"
        if score >= 60:
            return "Promising but needs validation"
        if score >= 45:
            return "Risky / needs more proof"
        return "Weak validation"

    def _prepare_startup_input(
        self,
        request: BusinessValidationRequest,
        startup_model_sector: str,
        feature_order: list[str],
    ) -> Any:
        safe_team_size = max(request.team_size, 1)
        safe_revenue = self._normalize_revenue_for_training(request.revenue_million)
        row = {
            "funding_rounds": int(max(request.funding_rounds, 1)),
            "founder_experience_years": float(request.founder_experience_years),
            "team_size": int(safe_team_size),
            "market_size_billion": float(request.market_size_billion),
            "product_traction_users": int(max(request.product_traction_users, 0)),
            "burn_rate_million": float(max(request.burn_rate_million, 0)),
            "investor_type": request.investor_type,
            "sector": startup_model_sector,
            "founder_background": request.founder_background,
            "traction_per_employee": float(request.product_traction_users) / safe_team_size,
            "burn_to_revenue_ratio": float(request.burn_rate_million) / safe_revenue,
        }

        try:
            import pandas as pd

            return pd.DataFrame([{feature: row.get(feature) for feature in feature_order}])
        except Exception as exc:
            raise RuntimeError("pandas is required for startup model inference") from exc

    def _heuristic_startup_score(self, request: BusinessValidationRequest) -> float:
        experience = self._normalize_positive(request.founder_experience_years, 0, 20)
        rounds = self._normalize_positive(request.funding_rounds, 1, 8)
        team = self._normalize_positive(request.team_size, 1, 250)
        market = self._normalize_positive(request.market_size_billion, 0.2, 80)
        traction = self._normalize_positive(request.product_traction_users, 0, 1_000_000)
        burn_penalty = self._normalize_positive(request.burn_rate_million, 0, 50)
        return self._bounded(
            0.20 * experience
            + 0.15 * rounds
            + 0.15 * team
            + 0.20 * market
            + 0.25 * traction
            + 0.05 * (100 - burn_penalty)
        )

    def _keyword_sentiment_score(self, opinions: list[str]) -> float:
        scores = []
        for opinion in opinions:
            tokens = set(self._clean_text(opinion).split())
            pos = len(tokens & POSITIVE_WORDS)
            neg = len(tokens & NEGATIVE_WORDS)
            if pos == neg:
                scores.append(50.0)
            else:
                scores.append(100.0 * pos / max(pos + neg, 1))
        return float(sum(scores) / len(scores))

    def _artifact_value(self, key: str, default: Any) -> Any:
        if isinstance(self.startup_artifact, dict):
            return self.startup_artifact.get(key, default)
        return default

    @staticmethod
    def _extract_pipeline(artifact: Any) -> Any:
        if artifact is None:
            return None
        if isinstance(artifact, dict):
            return artifact.get("pipeline") or artifact.get("model")
        return artifact

    @staticmethod
    def _pipeline_classes(pipeline: Any) -> list[Any] | None:
        if hasattr(pipeline, "classes_"):
            return list(pipeline.classes_)
        if hasattr(pipeline, "named_steps"):
            for step in reversed(list(pipeline.named_steps.values())):
                if hasattr(step, "classes_"):
                    return list(step.classes_)
        return None

    @staticmethod
    def _positive_class_index(classes: list[Any] | None) -> int:
        if not classes:
            return 1
        normalized = [str(value).lower() for value in classes]
        for positive_value in ["1", "success", "true"]:
            if positive_value in normalized:
                return normalized.index(positive_value)
        return min(1, len(classes) - 1)

    @staticmethod
    def _is_positive_prediction(prediction: Any) -> bool:
        normalized = str(prediction).lower()
        return normalized in {"1", "success", "true"}

    @staticmethod
    def _normalize_revenue_for_training(revenue_value: float) -> float:
        """Match the scale used by the saved startup model.

        The training CSV column is named revenue_million, but its values are in
        the hundreds of thousands/millions range. The app asks users for revenue
        in millions, so 0.3 means 0.3M and must become 300000 for the engineered
        burn_to_revenue_ratio used by the trained pipeline.
        """
        revenue = max(float(revenue_value or 0), 1e-6)
        if revenue < 10_000:
            revenue *= 1_000_000
        return max(revenue, 1e-6)

    @staticmethod
    def _load_joblib(path: Path) -> Any:
        if not path.exists():
            return None
        try:
            import joblib

            return joblib.load(path)
        except Exception:
            return None

    @staticmethod
    def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
        total = sum(max(float(value), 0.0) for value in weights.values())
        if total <= 0:
            return DEFAULT_WEIGHTS.copy()
        return {key: max(float(value), 0.0) / total for key, value in weights.items()}

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", str(value).lower().strip())

    @staticmethod
    def _bounded(value: float, low: float = 0.0, high: float = 100.0) -> float:
        if math.isnan(value) or math.isinf(value):
            return 50.0
        return max(low, min(high, float(value)))

    def _normalize_positive(self, value: float, low: float, high: float) -> float:
        if high <= low:
            return 50.0
        return self._bounded((float(value) - low) / (high - low) * 100)

    def _competition_to_score(self, value: str | float | None) -> float:
        if value is None:
            return 55.0
        if isinstance(value, (int, float)):
            return 100.0 - self._bounded(float(value))
        normalized = self._clean_text(value)
        mapping = {
            "low": 85.0,
            "faible": 85.0,
            "medium": 60.0,
            "moyen": 60.0,
            "high": 35.0,
            "eleve": 35.0,
            "elevé": 35.0,
        }
        return mapping.get(normalized, 55.0)

    @staticmethod
    def _structured_data_completeness(request: BusinessValidationRequest) -> float:
        fields = [
            request.project_description,
            request.sector,
            request.funding_rounds,
            request.founder_experience_years,
            request.team_size,
            request.market_size_billion,
            request.product_traction_users,
            request.burn_rate_million,
            request.revenue_million,
            request.investor_type,
            request.founder_background,
            request.country,
        ]
        available = sum(value not in [None, "", 0] for value in fields)
        return available / len(fields)


DEFAULT_STARTUP_FEATURES = [
    "funding_rounds",
    "founder_experience_years",
    "team_size",
    "market_size_billion",
    "product_traction_users",
    "burn_rate_million",
    "investor_type",
    "sector",
    "founder_background",
    "traction_per_employee",
    "burn_to_revenue_ratio",
]


def score_business_idea(payload: dict[str, Any]) -> dict[str, Any]:
    engine = BusinessValidationScoreEngine()
    return asdict(engine.validate(payload))


if __name__ == "__main__":
    example = {
        "project_name": "Smart real-estate platform",
        "project_description": "A platform that helps users compare houses, prices and neighborhoods.",
        "sector": "real estate",
        "funding_rounds": 1,
        "founder_experience_years": 5,
        "team_size": 8,
        "market_size_billion": 25,
        "product_traction_users": 12000,
        "burn_rate_million": 0.8,
        "revenue_million": 0.3,
        "investor_type": "angel",
        "founder_background": "first_time",
        "market_growth_rate_percent": 8,
        "competition_level": "high",
        "specialist_match_score": 72,
        "risk_score": 38,
        "opinions": [
            "Users like the idea because finding houses is difficult.",
            "Some people complain about high prices and trust issues.",
        ],
    }
    print(score_business_idea(example))
