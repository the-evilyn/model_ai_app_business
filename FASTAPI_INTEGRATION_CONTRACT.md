# FastAPI Integration Contract

Local URLs:

- Main AI API: `http://127.0.0.1:8004`
- Chatbot API: `http://127.0.0.1:8003`

Architecture:

```text
Angular -> Spring Boot -> FastAPI IA
```

Angular should not call FastAPI directly.

## Endpoints

| Purpose | Method | FastAPI endpoint | Spring Boot responsibility | MongoDB classes |
|---|---:|---|---|---|
| Health check | GET | `/health` | Optional admin/diagnostic check | none |
| Model status | GET | `/api/v1/models/status` | Optional admin/diagnostic check | none |
| Startup success prediction | POST | `/api/v1/startup-success/predict` | Call when analyzing startup success | `Project`, `BusinessIdeaAnalysis` |
| Market opinion sentiment | POST | `/api/v1/sentiment/analyze` | Send feedback texts collected from users | `MarketFeedback`, `SentimentAnalysis` |
| Market analysis | POST | `/api/v1/market-analysis/score` | Call when analyzing market potential | `Project`, `MarketAnalysis` |
| Specialist recommendation | POST | `/api/v1/specialists/recommend` | Send generated needs and available specialists | `SpecialistRecommendation` |
| Business validation score | POST | `/api/v1/business-validation/score` | Call for score-only validation | `Project`, `BusinessIdeaAnalysis`, `MarketAnalysis` |
| Full business analysis | POST | `/api/v1/business-validation/analyze` | Preferred endpoint for complete project analysis | `Project`, `BusinessIdeaAnalysis`, `MarketAnalysis`, `MarketFeedback`, `SentimentAnalysis`, `SpecialistRecommendation` |
| Report content | POST | `/api/v1/reports/generate-content` | Generate report text before Spring creates PDF | `Report`, `Project`, `BusinessIdeaAnalysis` |
| Chatbot status | GET | `/api/v1/chatbot/status` | Optional chatbot diagnostic check | none |
| Chatbot message | POST | `/api/v1/chatbot/message` | Send user chat message and project context | `Chat`, `Message`, `AIRequest`, `AIResponse`, `Project` |

## Shared Project Payload

```json
{
  "project_name": "NexusAI Business Validator",
  "project_description": "A SaaS platform that uses AI and market data to validate startup ideas.",
  "sector": "SaaS",
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
  "competition_level": "medium",
  "search_trend_score": 65,
  "country": "Morocco",
  "country_code": "MAR",
  "keyword": "business validation",
  "use_world_bank": false,
  "opinions": [
    "Customers like the idea because validation is difficult.",
    "Some users complain that consulting is expensive."
  ]
}
```

## Startup Success Input Units

Spring Boot must send values to FastAPI using the application input units below. FastAPI handles the internal transformations needed to match the training dataset.

| Field | Unit expected from Spring Boot | Internal transformation before prediction |
|---|---|---|
| `revenue_million` | Millions. Example: `0.5` means 0.5 million | Converted to training scale: `0.5 -> 500000` |
| `burn_rate_million` | Same app unit used by the trained dataset feature | Used directly |
| `product_traction_users` | Number of users | Used directly |
| `team_size` | Number of team members | Used directly, minimum denominator is 1 |

Engineered features used by the saved Startup Success pipeline:

```text
traction_per_employee = product_traction_users / max(team_size, 1)
burn_to_revenue_ratio = burn_rate_million / normalized_revenue
```

Where:

```text
normalized_revenue = revenue_million * 1_000_000  if revenue_million < 10_000
normalized_revenue = revenue_million              otherwise
```

Example:

```text
revenue_million = 0.5
burn_rate_million = 0.7
normalized_revenue = 500000
burn_to_revenue_ratio = 0.7 / 500000 = 1.4e-06
```

This conversion is required because the training dataset column is named `revenue_million`, but its stored values are in the hundreds of thousands / millions scale. Spring Boot should not pre-convert this field; it should send the application value, and FastAPI will normalize it.

## Response Shapes

### `POST /api/v1/startup-success/predict`

Returns:

```json
{
  "success_probability": 7.34,
  "prediction_label": "Failure",
  "model_loaded": true,
  "model_mode": "trained_model",
  "explanation": {
    "method": "SHAP",
    "fallback": false,
    "positiveFactors": [
      {
        "feature": "burn_to_revenue_ratio",
        "label": "Ratio dépenses / revenus",
        "value": 1.4e-06,
        "impact": 1.9119,
        "interpretation": "Un ratio dépenses / revenus favorable contribue positivement à la prédiction."
      }
    ],
    "negativeFactors": [
      {
        "feature": "burn_rate_million",
        "label": "Dépenses mensuelles",
        "value": 0.7,
        "impact": -1.3833,
        "interpretation": "Des dépenses mensuelles élevées contribuent négativement à la prédiction."
      }
    ]
  }
}
```

### `POST /api/v1/sentiment/analyze`

Payload:

```json
{ "texts": ["Customer feedback 1", "Customer feedback 2"] }
```

Returns:

```json
{
  "average_sentiment_score": 33.82,
  "overall_label": "negative",
  "model_loaded": true,
  "model_mode": "trained_pipeline",
  "count": 2,
  "results": [
    { "text": "Customer feedback 1", "sentiment_score": 50.0, "sentiment_label": "positive" }
  ]
}
```

### `POST /api/v1/market-analysis/score`

Returns:

```json
{
  "market_analysis": {
    "market_score": 53.18,
    "market_label": "Moderate / needs validation",
    "confidence_score": 100.0,
    "normalized_sector": "SaaS",
    "sub_scores": {}
  },
  "features": {}
}
```

### `POST /api/v1/specialists/recommend`

Payload:

```json
{
  "title": "NexusAI Business Validator",
  "description": "A SaaS platform...",
  "sector": "SaaS",
  "needs": ["market research", "go-to-market", "AI"],
  "budget_per_hour": 80,
  "preferred_language": "fr",
  "location": "Morocco",
  "top_k": 3
}
```

Returns:

```json
{
  "count": 3,
  "recommendations": [
    {
      "specialist_id": "sample_001",
      "full_name": "Example Specialist",
      "expertise_domain": "Market Research",
      "recommended_score": 80,
      "reason": "..."
    }
  ],
  "source": "sample_csv"
}
```

### `POST /api/v1/business-validation/analyze`

Preferred complete analysis endpoint. Returns:

```json
{
  "scores": {
    "finalScore": 27.71,
    "startupSuccessScore": 7.34,
    "marketAnalysisScore": 53.18,
    "marketOpinionScore": 33.82
  },
  "startupPrediction": {},
  "shapExplanation": {
    "method": "SHAP",
    "fallback": false,
    "positiveFactors": [
      {
        "feature": "burn_to_revenue_ratio",
        "label": "Ratio dépenses / revenus",
        "value": 1.4e-06,
        "impact": 1.9119,
        "interpretation": "Un ratio dépenses / revenus favorable contribue positivement à la prédiction."
      }
    ],
    "negativeFactors": [
      {
        "feature": "burn_rate_million",
        "label": "Dépenses mensuelles",
        "value": 0.7,
        "impact": -1.3833,
        "interpretation": "Des dépenses mensuelles élevées contribuent négativement à la prédiction."
      }
    ]
  },
  "strengths": [],
  "weaknesses": [],
  "recommendations": [],
  "warnings": [],
  "generatedNeeds": [],
  "recommendedSpecialists": [],
  "interpretation": "...",
  "interpretationSource": "nvidia_llm",
  "createdAt": "2026-05-30T00:00:00+00:00"
}
```

Scores are generated by trained models or deterministic scoring only. NVIDIA generates interpretation text and lists only.

### `POST /api/v1/reports/generate-content`

Payload:

```json
{
  "projectData": {},
  "analysisResult": {},
  "includeBusinessPlan": true
}
```

Returns report text content:

```json
{
  "title": "Rapport de validation business - Project Name",
  "executiveSummary": "...",
  "analysisSummary": "...",
  "strengths": [],
  "weaknesses": [],
  "recommendations": [],
  "businessPlan": {},
  "warnings": [],
  "generationSource": "nvidia_llm"
}
```

Spring Boot remains responsible for PDF generation.

### `POST /api/v1/chatbot/message`

Payload:

```json
{
  "message": "Génère un business plan court pour ce projet.",
  "project_data": {},
  "conversation_history": [],
  "chat_id": "chat-id",
  "user_id": "user-id",
  "fast_mode": true
}
```

Returns:

```json
{
  "intent": "business_plan",
  "answer": "Natural language answer for the user.",
  "api_results": {},
  "api_errors": {},
  "rag_context": [],
  "recommendations": [],
  "sources_used": [],
  "memory_saved": {},
  "fallback_mode": false
}
```

The field `answer` is user-visible natural language, not a technical JSON blob.
