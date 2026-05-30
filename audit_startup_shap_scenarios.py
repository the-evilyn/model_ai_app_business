from __future__ import annotations

import json

from fastapi.testclient import TestClient

import business_validation_api as api


BASE = {
    "project_name": "Scenario",
    "project_description": "A SaaS startup project.",
    "sector": "SaaS",
    "investor_type": "angel",
    "founder_background": "first_time",
}


SCENARIOS = {
    "weak": {
        **BASE,
        "funding_rounds": 1,
        "founder_experience_years": 0,
        "team_size": 2,
        "market_size_billion": 0.5,
        "product_traction_users": 50,
        "burn_rate_million": 2.0,
        "revenue_million": 0.001,
    },
    "medium": {
        **BASE,
        "funding_rounds": 2,
        "founder_experience_years": 4,
        "team_size": 10,
        "market_size_billion": 8,
        "product_traction_users": 15000,
        "burn_rate_million": 0.7,
        "revenue_million": 0.5,
    },
    "strong": {
        **BASE,
        "funding_rounds": 5,
        "founder_experience_years": 12,
        "team_size": 45,
        "market_size_billion": 80,
        "product_traction_users": 500000,
        "burn_rate_million": 0.4,
        "revenue_million": 8.0,
        "investor_type": "tier1_vc",
        "founder_background": "ex_bigtech",
    },
}


def compact_explanation(explanation: dict) -> dict:
    return {
        "method": explanation.get("method"),
        "fallback": explanation.get("fallback"),
        "positiveFactors": explanation.get("positiveFactors", [])[:3],
        "negativeFactors": explanation.get("negativeFactors", [])[:3],
    }


def main() -> None:
    client = TestClient(api.app)
    results = {}
    for name, payload in SCENARIOS.items():
        response = client.post("/api/v1/startup-success/predict", json=payload)
        body = response.json()
        results[name] = {
            "status_code": response.status_code,
            "success_probability": body.get("success_probability"),
            "prediction_label": body.get("prediction_label"),
            "model_mode": body.get("model_mode"),
            "explanation": compact_explanation(body.get("explanation", {})),
        }

    analyze_payload = {
        **SCENARIOS["medium"],
        "market_growth_rate_percent": 8,
        "competition_level": "medium",
        "search_trend_score": 65,
        "country": "Morocco",
        "country_code": "MAR",
        "keyword": "business validation",
        "use_world_bank": False,
        "opinions": [
            "Customers like the idea because validation is difficult.",
            "Some users complain that consulting is expensive.",
        ],
    }
    analyze = client.post("/api/v1/business-validation/analyze", json=analyze_payload).json()
    results["business_validation_analyze"] = {
        "scores": analyze.get("scores"),
        "shapExplanation": analyze.get("shapExplanation"),
        "strengths": analyze.get("strengths"),
        "weaknesses": analyze.get("weaknesses"),
        "generatedNeeds": analyze.get("generatedNeeds"),
        "recommendedSpecialists": [
            {
                "full_name": item.get("full_name"),
                "expertise_domain": item.get("expertise_domain"),
                "recommended_score": item.get("recommended_score"),
                "reason": item.get("reason"),
            }
            for item in analyze.get("recommendedSpecialists", [])[:3]
        ],
        "interpretationSource": analyze.get("interpretationSource"),
    }
    print(json.dumps(results, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
