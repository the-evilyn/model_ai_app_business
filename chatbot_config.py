"""
chatbot_config.py
─────────────────
Central configuration for the NexusAI Business Chatbot.

All secrets are loaded from environment variables (via python-dotenv).
No API key is ever hard-coded.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    _env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(_env_path, override=True)
except ImportError:
    pass  # python-dotenv is optional; rely on real env vars


# ─────────────────────────────── API URLs ────────────────────────────────── #

FASTAPI_BASE_URL: str = os.getenv("FASTAPI_BASE_URL", "http://127.0.0.1:8000")
CHATBOT_API_PORT: int = int(os.getenv("CHATBOT_API_PORT", "8002"))

# ──────────────────────────── LLM Provider ───────────────────────────────── #

LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "none").lower()
LLM_MODEL: str = os.getenv("LLM_MODEL", "")
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))

# Provider-specific API keys
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

# OpenRouter settings (OpenAI-compatible API at a different base URL)
OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Default models per provider (used when LLM_MODEL is empty)
DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-1.5-flash",
    "mistral": "mistral-small-latest",
    "claude": "claude-sonnet-4-20250514",
    "openrouter": "openai/gpt-4o-mini",
}

# ──────────────────────────── Timeouts ───────────────────────────────────── #

API_TIMEOUT_SECONDS: int = int(os.getenv("API_TIMEOUT_SECONDS", "30"))
LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))

# ──────────────────────────── RAG Settings ───────────────────────────────── #

RAG_ENABLED: bool = os.getenv("RAG_ENABLED", "true").lower() in ("true", "1", "yes")
RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "2"))
CHATBOT_FAST_MODE: bool = os.getenv("CHATBOT_FAST_MODE", "false").lower() == "true"
KNOWLEDGE_DOCS_PATH: str = os.getenv(
    "KNOWLEDGE_DOCS_PATH",
    str(Path(__file__).resolve().parent / "data" / "knowledge_documents.json"),
)

# ──────────────────────────── Memory Settings ────────────────────────────── #

MEMORY_BACKEND: str = os.getenv("MEMORY_BACKEND", "local")  # "local" | "mongodb"
MEMORY_FILE_PATH: str = os.getenv(
    "MEMORY_FILE_PATH",
    str(Path(__file__).resolve().parent / "data" / "chat_memory.json"),
)
MONGODB_URI: str = os.getenv("MONGODB_URI", "")
MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "nexusai")

# ────────────────── Existing API Endpoints ───────────────────────────────── #

ENDPOINTS: dict[str, str] = {
    "health": f"{FASTAPI_BASE_URL}/health",
    "models_status": f"{FASTAPI_BASE_URL}/api/v1/models/status",
    "startup_success": f"{FASTAPI_BASE_URL}/api/v1/startup-success/predict",
    "sentiment": f"{FASTAPI_BASE_URL}/api/v1/sentiment/analyze",
    "market_analysis": f"{FASTAPI_BASE_URL}/api/v1/market-analysis/score",
    "specialists": f"{FASTAPI_BASE_URL}/api/v1/specialists/recommend",
    "business_validation": f"{FASTAPI_BASE_URL}/api/v1/business-validation/score",
}

# ────────────────── Intent Detection Keywords ────────────────────────────── #

INTENT_KEYWORDS: dict[str, list[str]] = {
    "startup_analysis": [
        "startup", "predict success", "success probability", "startup idea",
        "analyze my startup", "startup score", "chance of success",
        "will my startup succeed", "startup prediction", "predict my startup",
        "idée startup", "analyser mon startup", "probabilité de succès",
    ],
    "market_analysis": [
        "market", "market potential", "market size", "market growth",
        "market score", "market opportunity", "market trends", "competition",
        "marché", "potentiel du marché", "taille du marché", "analyse du marché",
    ],
    "sentiment_analysis": [
        "sentiment", "opinion", "review", "feedback", "customer review",
        "analyze reviews", "customer feedback", "user opinion", "what do users think",
        "avis", "opinions", "sentiments", "commentaires clients",
    ],
    "specialist_recommendation": [
        "specialist", "recommend specialist", "find expert", "which expert",
        "consultant", "hire specialist", "need expert", "who can help",
        "spécialiste", "recommander un spécialiste", "trouver un expert",
    ],
    "business_validation": [
        "validate", "business validation", "validation score", "overall score",
        "validate my business", "business score", "final score", "validate idea",
        "valider", "score de validation", "valider mon projet", "score final",
    ],
    "business_recommendation": [
        "improve", "recommendation", "how can i improve", "what should i change",
        "suggestions", "advice", "optimize", "strengthen", "weakness",
        "améliorer", "recommandation", "conseils", "optimiser",
    ],
    "marketing_strategy": [
        "marketing", "marketing strategy", "go to market", "growth strategy",
        "customer acquisition", "brand strategy", "marketing plan", "promote",
        "stratégie marketing", "plan marketing", "acquisition clients",
    ],
    "business_plan": [
        "business plan", "generate plan", "create plan", "financial plan",
        "roadmap", "pitch deck", "executive summary", "plan d'affaires",
        "plan business", "générer un plan",
    ],
    "report_summary": [
        "report", "summary", "summarize", "generate report", "pdf report",
        "overview", "résumé", "rapport", "synthèse", "générer un rapport",
    ],
    "general_question": [
        "hello", "hi", "help", "what can you do", "explain", "tell me about",
        "how does it work", "what is", "bonjour", "salut", "aide",
    ],
}

# ──────────────────────────── Helpers ────────────────────────────────────── #


def get_api_key_for_provider(provider: str) -> str:
    """Return the API key configured for the given provider."""
    mapping = {
        "openai": OPENAI_API_KEY,
        "gemini": GEMINI_API_KEY,
        "mistral": MISTRAL_API_KEY,
        "claude": CLAUDE_API_KEY,
        "openrouter": OPENROUTER_API_KEY,
    }
    return mapping.get(provider, "")


def get_effective_model(provider: str) -> str:
    """Return the model name to use, falling back to provider defaults."""
    if LLM_MODEL:
        return LLM_MODEL
    return DEFAULT_MODELS.get(provider, "")


def is_llm_configured() -> bool:
    """Return True when a valid provider + key pair is present."""
    if LLM_PROVIDER in ("none", ""):
        return False
    return bool(get_api_key_for_provider(LLM_PROVIDER))


def is_fallback_mode() -> bool:
    """True when the chatbot will use template responses instead of an LLM."""
    return not is_llm_configured()
