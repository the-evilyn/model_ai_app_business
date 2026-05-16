from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from business_validation_score_engine import BusinessValidationRequest, BusinessValidationScoreEngine
from market_analysis_score_engine import MarketAnalysisScoreEngine
from market_data_collector import MarketDataCollector
from specialist_recommendation_engine import SpecialistRecommendationEngine


app = FastAPI(
    title="NexusAI Business Validation API",
    version="0.2.0",
    description="AI services for startup validation, sentiment analysis, market scoring and specialist recommendation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = BusinessValidationScoreEngine()
market_engine = MarketAnalysisScoreEngine()
market_collector = MarketDataCollector()
specialist_engine = SpecialistRecommendationEngine()


def _model_to_dict(model: BaseModel, *, exclude_none: bool = False) -> dict[str, Any]:
    """Support both Pydantic v1 (.dict) and v2 (.model_dump)."""
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=exclude_none)
    return model.dict(exclude_none=exclude_none)


class BusinessValidationPayload(BaseModel):
    project_name: str
    project_description: str
    sector: str
    funding_rounds: int = Field(default=1, ge=1)
    founder_experience_years: float = Field(default=0.0, ge=0)
    team_size: int = Field(default=1, ge=1)
    market_size_billion: float = Field(default=1.0, ge=0)
    product_traction_users: int = Field(default=0, ge=0)
    burn_rate_million: float = Field(default=0.0, ge=0)
    revenue_million: float = Field(default=0.000001, ge=0)
    investor_type: str = "none"
    founder_background: str = "first_time"
    market_growth_rate_percent: float | None = None
    competition_level: str | float | None = None
    search_trend_score: float | None = Field(default=None, ge=0, le=100)
    country: str | None = "Morocco"
    region: str | None = None
    country_code: str | None = None
    keyword: str | None = None
    google_trends_csv_path: str | None = None
    use_world_bank: bool = False
    specialist_match_score: float | None = Field(default=None, ge=0, le=100)
    risk_score: float | None = Field(default=None, ge=0, le=100)
    opinions: list[str] = Field(default_factory=list)


class StartupSuccessPayload(BaseModel):
    project_name: str = "Untitled project"
    project_description: str = ""
    sector: str
    funding_rounds: int = Field(default=1, ge=1)
    founder_experience_years: float = Field(default=0.0, ge=0)
    team_size: int = Field(default=1, ge=1)
    market_size_billion: float = Field(default=1.0, ge=0)
    product_traction_users: int = Field(default=0, ge=0)
    burn_rate_million: float = Field(default=0.0, ge=0)
    revenue_million: float = Field(default=0.000001, ge=0)
    investor_type: str = "none"
    founder_background: str = "first_time"


class SentimentPayload(BaseModel):
    texts: list[str] = Field(default_factory=list)


class SpecialistPayload(BaseModel):
    specialist_id: str | None = None
    id: str | None = None
    full_name: str | None = None
    fullName: str | None = None
    expertise_domain: str | None = None
    expertiseDomain: str | None = None
    profession: str | None = None
    skills: list[str] | str = Field(default_factory=list)
    sectors: list[str] | str = Field(default_factory=list)
    industry_experience: int | None = None
    industryExperience: int | None = None
    experienceYears: int | None = None
    hourly_rate: float | None = None
    hourlyRate: float | None = None
    languages: list[str] | str = Field(default_factory=list)
    location: str = ""
    average_rating: float | None = None
    averageRating: float | None = None
    rating: float | None = None
    reviews_count: int | None = None
    reviewsCount: int | None = None
    availability_status: str | None = None
    availabilityStatus: str | None = None
    bio: str = ""
    completed_projects: int | None = None
    completedProjects: int | None = None


class MarketAnalysisPayload(BaseModel):
    project_name: str = "Untitled project"
    sector: str
    country: str = "Morocco"
    country_code: str | None = None
    keyword: str | None = None
    market_size_billion: float | None = Field(default=None, ge=0)
    market_growth_rate_percent: float | None = None
    competition_level: str | None = None
    competition_count: int | None = Field(default=None, ge=0)
    product_traction_users: int | None = Field(default=None, ge=0)
    search_trend_score: float | None = Field(default=None, ge=0, le=100)
    google_trends_csv_path: str | None = None
    use_world_bank: bool = True


class SpecialistRecommendationPayload(BaseModel):
    project_id: str | None = None
    title: str
    description: str
    sector: str
    needs: list[str] = Field(default_factory=list)
    project_stage: str | None = None
    budget_per_hour: float | None = Field(default=None, ge=0)
    preferred_language: str | None = None
    location: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    specialists: list[SpecialistPayload] | None = None


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "NexusAI Business Validation API",
        "version": app.version,
    }


@app.get("/api/v1/models/status")
def models_status() -> dict[str, Any]:
    return {
        "startup_success": {
            "artifact_path": str(engine.startup_model_path),
            "loaded": engine.startup_artifact is not None,
            "fallback": engine.startup_artifact is None,
        },
        "sentiment_analysis": {
            "artifact_path": str(engine.sentiment_model_path),
            "loaded": engine.sentiment_artifact is not None,
            "fallback": engine.sentiment_artifact is None,
        },
        "market_analysis": {
            "type": "data-driven scoring engine",
            "sources": ["World Bank Indicators API", "Google Trends CSV optional", "project inputs"],
            "loaded": True,
        },
        "specialist_recommendation": {
            "type": "hybrid recommender",
            "source": "MongoDB specialists in production, sample CSV in demo",
            "loaded": True,
        },
    }


@app.post("/api/v1/startup-success/predict")
def predict_startup_success(payload: StartupSuccessPayload) -> dict[str, Any]:
    payload_dict = _model_to_dict(payload)
    request = BusinessValidationRequest(**payload_dict)
    sector_info = engine.normalize_sector(payload.sector, payload.project_description)
    score = engine.startup_success_score(request, sector_info["startup_model_sector"])
    return {
        "success_probability": round(score, 2),
        "prediction_label": "Success" if score >= 50 else "Failure",
        "model_loaded": engine.startup_artifact is not None,
        "model_mode": "trained_model" if engine.startup_artifact is not None else "fallback_heuristic",
        "important_note": (
            "Revenue is entered in millions in the app. During inference it is converted "
            "to the same scale used by the training dataset for burn_to_revenue_ratio."
        ),
        "sector": {
            "original": payload.sector,
            **sector_info,
        },
        "final_engine_context": {
            "used_features": payload_dict,
            "warning": "Sector confidence is reduced when startup_model_sector is Other.",
        },
    }


@app.post("/api/v1/sentiment/analyze")
def analyze_sentiment(payload: SentimentPayload) -> dict[str, Any]:
    texts = [text.strip() for text in payload.texts if text.strip()]
    if not texts:
        raise HTTPException(status_code=400, detail="At least one non-empty text is required.")
    results = []
    for text in texts:
        score = engine.market_sentiment_score([text])
        results.append(
            {
                "text": text,
                "sentiment_score": round(score, 2),
                "sentiment_label": "positive" if score >= 50 else "negative",
            }
        )

    average_score = sum(item["sentiment_score"] for item in results) / len(results)
    return {
        "average_sentiment_score": round(average_score, 2),
        "overall_label": "positive" if average_score >= 50 else "negative",
        "model_loaded": engine.sentiment_artifact is not None,
        "model_mode": "trained_pipeline" if engine.sentiment_artifact is not None else "fallback_keywords",
        "count": len(results),
        "results": results,
    }


@app.post("/api/v1/business-validation/score")
def score_business(payload: BusinessValidationPayload) -> dict[str, Any]:
    payload_dict = _model_to_dict(payload, exclude_none=True)
    collected_features = None

    if payload.use_world_bank or payload.google_trends_csv_path:
        trend_path = payload.google_trends_csv_path
        collected = market_collector.collect_project_features(
            payload_dict,
            google_trends_csv_path=Path(trend_path) if trend_path else None,
            use_world_bank=payload.use_world_bank,
        )
        collected_features = asdict(collected)
        for key in ["market_size_billion", "market_growth_rate_percent", "search_trend_score", "country"]:
            if payload.use_world_bank and collected_features.get(key) is not None:
                payload_dict[key] = collected_features[key]
            elif payload_dict.get(key) is None and collected_features.get(key) is not None:
                payload_dict[key] = collected_features[key]

    allowed_fields = {item.name for item in fields(BusinessValidationRequest)}
    result = engine.validate({key: value for key, value in payload_dict.items() if key in allowed_fields})
    response = result.__dict__
    response["market_collected_features"] = collected_features
    return response


@app.post("/api/v1/market-analysis/score")
def score_market(payload: MarketAnalysisPayload) -> dict[str, Any]:
    payload_dict = _model_to_dict(payload, exclude_none=True)
    trend_path = payload.google_trends_csv_path
    collected = market_collector.collect_project_features(
        payload_dict,
        google_trends_csv_path=Path(trend_path) if trend_path else None,
        use_world_bank=payload.use_world_bank,
    )
    analysis_payload = asdict(collected)
    if analysis_payload.get("search_trend_score") is None and payload.search_trend_score is not None:
        analysis_payload["search_trend_score"] = payload.search_trend_score

    result = market_engine.analyze(analysis_payload)
    return {
        "market_analysis": result.__dict__,
        "features": analysis_payload,
    }


@app.post("/api/v1/specialists/recommend")
def recommend_specialists(payload: SpecialistRecommendationPayload) -> dict[str, Any]:
    specialists = None
    if payload.specialists is not None:
        specialists = [_model_to_dict(item, exclude_none=True) for item in payload.specialists]

    recommendations = specialist_engine.recommend(
        {
            "project_id": payload.project_id,
            "title": payload.title,
            "description": payload.description,
            "sector": payload.sector,
            "needs": payload.needs,
            "project_stage": payload.project_stage,
            "budget_per_hour": payload.budget_per_hour,
            "preferred_language": payload.preferred_language,
            "location": payload.location,
            "top_k": payload.top_k,
        },
        specialists=specialists,
    )

    return {
        "count": len(recommendations),
        "recommendations": [item.__dict__ for item in recommendations],
        "source": "request_specialists" if specialists is not None else "sample_csv",
    }
