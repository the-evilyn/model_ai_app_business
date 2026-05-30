from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from business_validation_score_engine import BusinessValidationRequest, BusinessValidationScoreEngine
from interpretability_engine import StartupInterpretabilityEngine
from analysis_interpretation_engine import (
    build_business_interpretation,
    build_warnings,
    utc_now_iso,
)
from market_analysis_score_engine import MarketAnalysisScoreEngine
from market_data_collector import MarketDataCollector
from report_content_engine import generate_report_content
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
interpretability_engine = StartupInterpretabilityEngine(engine)


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
    project_stage: str | None = None
    budget_per_hour: float | None = Field(default=None, ge=0)
    preferred_language: str | None = None
    specialists: list["SpecialistPayload"] | None = None


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


class ReportContentPayload(BaseModel):
    projectData: dict[str, Any] = Field(default_factory=dict)
    analysisResult: dict[str, Any] = Field(default_factory=dict)
    includeBusinessPlan: bool = True


try:
    BusinessValidationPayload.model_rebuild()
except AttributeError:
    BusinessValidationPayload.update_forward_refs()


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
    explanation = interpretability_engine.explain(request, sector_info["startup_model_sector"])
    return {
        "success_probability": round(score, 2),
        "prediction_label": "Success" if score >= 50 else "Failure",
        "model_loaded": engine.startup_artifact is not None,
        "model_mode": "trained_model" if engine.startup_artifact is not None else "fallback_heuristic",
        "explanation": explanation,
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


@app.post("/api/v1/business-validation/analyze")
def analyze_business(payload: BusinessValidationPayload) -> dict[str, Any]:
    payload_dict = _model_to_dict(payload, exclude_none=True)
    allowed_fields = {item.name for item in fields(BusinessValidationRequest)}
    request_dict = {key: value for key, value in payload_dict.items() if key in allowed_fields}
    request = BusinessValidationRequest(**request_dict)
    sector_info = engine.normalize_sector(payload.sector, payload.project_description)

    startup_score = engine.startup_success_score(request, sector_info["startup_model_sector"])
    startup_prediction = {
        "predictionLabel": "Success" if startup_score >= 50 else "Failure",
        "successProbability": round(startup_score, 2),
        "modelMode": "trained_model" if engine.startup_artifact is not None else "fallback_heuristic",
    }
    shap_explanation = interpretability_engine.explain(request, sector_info["startup_model_sector"])

    market_result = market_engine.analyze(
        {
            "sector": payload.sector,
            "market_size_billion": payload.market_size_billion,
            "market_growth_rate_percent": payload.market_growth_rate_percent,
            "competition_level": payload.competition_level,
            "product_traction_users": payload.product_traction_users,
            "search_trend_score": payload.search_trend_score,
            "country": payload.country,
            "region": payload.region,
            "notes": payload.project_description,
        }
    )
    market_analysis = {
        "market_analysis": market_result.__dict__,
        "features": {
            "market_size_billion": payload.market_size_billion,
            "market_growth_rate_percent": payload.market_growth_rate_percent,
            "competition_level": payload.competition_level,
            "product_traction_users": payload.product_traction_users,
            "search_trend_score": payload.search_trend_score,
            "country": payload.country,
            "region": payload.region,
        },
    }

    feedbacks = [text.strip() for text in payload.opinions if text.strip()]
    market_opinion = None
    market_opinion_score = None
    if feedbacks:
        sentiment_scores = [engine.market_sentiment_score([text]) for text in feedbacks]
        market_opinion_score = round(sum(sentiment_scores) / len(sentiment_scores), 2)
        market_opinion = {
            "average_sentiment_score": market_opinion_score,
            "overall_label": "positive" if market_opinion_score >= 50 else "negative",
            "count": len(feedbacks),
        }

    validation_result = engine.validate(request)
    sentiment_for_final = market_opinion_score if market_opinion_score is not None else 50.0
    raw_final = (
        engine.weights["startup_success"] * startup_score
        + engine.weights["market_sentiment"] * sentiment_for_final
        + engine.weights["market_analysis"] * market_result.market_score
    )
    final_score = engine._bounded(raw_final * (0.85 + 0.15 * sector_info["sector_reliability"]))
    scores = {
        "finalScore": round(final_score, 2),
        "startupSuccessScore": round(startup_score, 2),
        "marketAnalysisScore": round(market_result.market_score, 2),
        "marketOpinionScore": market_opinion_score,
    }

    interpretation = build_business_interpretation(
        payload_dict,
        scores,
        startup_prediction,
        shap_explanation,
        market_analysis,
        market_opinion,
    )
    warnings = build_warnings(
        feedback_count=len(feedbacks),
        startup_model_mode=startup_prediction["modelMode"],
        market_analysis=market_analysis,
        confidence_score=validation_result.confidence_score,
    )
    warnings.extend(item for item in validation_result.warnings if item not in warnings)

    specialists = None
    if payload.specialists is not None:
        specialists = [_model_to_dict(item, exclude_none=True) for item in payload.specialists]
    recommendations = specialist_engine.recommend(
        {
            "project_id": None,
            "title": payload.project_name,
            "description": payload.project_description,
            "sector": payload.sector,
            "needs": interpretation["generatedNeeds"],
            "project_stage": payload.project_stage,
            "budget_per_hour": payload.budget_per_hour,
            "preferred_language": payload.preferred_language,
            "location": payload.country,
            "top_k": 5,
        },
        specialists=specialists,
    )

    return {
        "scores": scores,
        "startupPrediction": startup_prediction,
        "shapExplanation": {
            "positiveFactors": shap_explanation.get("positiveFactors", []),
            "negativeFactors": shap_explanation.get("negativeFactors", []),
            "method": shap_explanation.get("method"),
            "fallback": shap_explanation.get("fallback", False),
        },
        "strengths": interpretation["strengths"],
        "weaknesses": interpretation["weaknesses"],
        "recommendations": interpretation["recommendations"],
        "warnings": warnings,
        "generatedNeeds": interpretation["generatedNeeds"],
        "recommendedSpecialists": [item.__dict__ for item in recommendations],
        "interpretation": interpretation["interpretation"],
        "interpretationSource": interpretation["interpretationSource"],
        "createdAt": utc_now_iso(),
    }


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


@app.post("/api/v1/reports/generate-content")
def generate_report(payload: ReportContentPayload) -> dict[str, Any]:
    return generate_report_content(
        project_data=payload.projectData,
        analysis_result=payload.analysisResult,
        include_business_plan=payload.includeBusinessPlan,
    )
