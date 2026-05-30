from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from llm_client import generate_json_response, get_llm_provider


ALLOWED_NEEDS = [
    "finance",
    "business plan",
    "market research",
    "go-to-market",
    "marketing",
    "UX",
    "customer experience",
    "AI",
    "cybersecurity",
    "legal",
]


def build_business_interpretation(
    project_data: dict[str, Any],
    scores: dict[str, Any],
    startup_prediction: dict[str, Any],
    shap_explanation: dict[str, Any],
    market_analysis: dict[str, Any],
    market_opinion: dict[str, Any] | None,
) -> dict[str, Any]:
    deterministic = _deterministic_findings(shap_explanation, market_analysis, market_opinion, scores)
    llm_output = _ask_llm(
        project_data,
        scores,
        startup_prediction,
        shap_explanation,
        market_analysis,
        market_opinion,
        deterministic,
    )

    strengths = _clean_list(llm_output.get("strengths")) or deterministic["strengths"]
    weaknesses = _clean_list(llm_output.get("weaknesses")) or deterministic["weaknesses"]
    recommendations = _clean_list(llm_output.get("recommendations")) or _fallback_recommendations(weaknesses)
    interpretation = str(llm_output.get("interpretation") or deterministic["interpretation"])
    needs = map_weaknesses_to_needs(weaknesses, scores)
    provider_info = get_llm_provider()

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations,
        "interpretation": interpretation,
        "generatedNeeds": needs,
        "interpretationSource": (
            f"{provider_info['provider']}_llm" if provider_info["configured"] else "fallback_rules"
        ),
    }


def build_warnings(
    feedback_count: int,
    startup_model_mode: str,
    market_analysis: dict[str, Any],
    confidence_score: float | None,
) -> list[str]:
    warnings = []
    if feedback_count == 0:
        warnings.append("Aucun feedback marché n'a été analysé.")
    elif feedback_count < 5:
        warnings.append("Le score d'opinion repose sur peu de feedbacks.")
    if "fallback" in startup_model_mode.lower():
        warnings.append("Le modèle Startup Success fonctionne en mode fallback.")
    if _external_market_data_unavailable(market_analysis):
        warnings.append("Les données marché externes ne sont pas disponibles.")
    if confidence_score is not None and confidence_score < 60:
        warnings.append("La confiance de l'analyse est limitée.")
    return warnings


def map_weaknesses_to_needs(weaknesses: list[str], scores: dict[str, Any]) -> list[str]:
    text = " ".join(weaknesses).lower()
    needs: list[str] = []

    def add(*items: str) -> None:
        for item in items:
            if item in ALLOWED_NEEDS and item not in needs:
                needs.append(item)

    if re.search(r"burn|dépense|depense|revenu|revenue|finance|cash|rentabil", text):
        add("finance", "business plan")
    if re.search(r"traction|acquisition|visibil|marketing", text):
        add("marketing", "go-to-market")
    if re.search(r"concurr|competition|marché faible|market weak|marché.*faible|market.*low|potentiel marché|potentiel market", text):
        add("market research", "go-to-market")
    if re.search(
        r"expérience utilisateur|experience utilisateur|user experience|customer experience|"
        r"\bux\b|utilisabil|usability|interface|parcours|friction|satisfaction|"
        r"usage difficile|difficulté d'usage|difficulte d'usage|expérience client|experience client",
        text,
    ):
        add("UX", "customer experience")
    if re.search(r"expérience du fondateur|experience du fondateur|founder experience|fondateur.*limit|founder.*limited|premier lancement|first.?time", text):
        add("business plan")
    if re.search(r"\\bia\\b|\\bai\\b|intelligence artificielle|machine learning", text):
        add("AI")
    if re.search(r"sécurité|securite|security|cyber", text):
        add("cybersecurity")
    if re.search(r"juridique|legal|contrat|conform", text):
        add("legal")

    if scores.get("marketAnalysisScore", 100) < 50:
        add("market research", "go-to-market")
    return needs


def _ask_llm(
    project_data: dict[str, Any],
    scores: dict[str, Any],
    startup_prediction: dict[str, Any],
    shap_explanation: dict[str, Any],
    market_analysis: dict[str, Any],
    market_opinion: dict[str, Any] | None,
    deterministic: dict[str, Any],
) -> dict[str, Any]:
    system_prompt = """
Tu es un conseiller business. Les scores numériques fournis viennent des modèles IA et du système de scoring.
Tu ne dois jamais les modifier, les recalculer ou les corriger.
Tu dois uniquement interpréter les résultats et générer des forces, faiblesses et recommandations cohérentes.
Retourne uniquement un objet JSON valide avec: strengths, weaknesses, recommendations, interpretation.
"""
    payload = {
        "project": project_data,
        "scores": scores,
        "startupPrediction": startup_prediction,
        "shapExplanation": shap_explanation,
        "marketAnalysis": market_analysis,
        "marketOpinion": market_opinion,
        "deterministicSignals": deterministic,
    }
    response = generate_json_response(system_prompt, json.dumps(payload, ensure_ascii=False))
    return response.get("json") or {}


def _deterministic_findings(
    shap_explanation: dict[str, Any],
    market_analysis: dict[str, Any],
    market_opinion: dict[str, Any] | None,
    scores: dict[str, Any],
) -> dict[str, Any]:
    strengths = [
        f"{item.get('label', item.get('feature'))} favorable."
        for item in shap_explanation.get("positiveFactors", [])[:3]
    ]
    weaknesses = [
        f"{item.get('label', item.get('feature'))} défavorable."
        for item in shap_explanation.get("negativeFactors", [])[:3]
    ]

    market_score = scores.get("marketAnalysisScore")
    opinion_score = scores.get("marketOpinionScore")
    if market_score is not None and market_score >= 60:
        strengths.append("Le potentiel marché est encourageant.")
    elif market_score is not None and market_score < 50:
        weaknesses.append("Le potentiel marché reste à valider.")

    if opinion_score is not None and opinion_score >= 60:
        strengths.append("L'opinion marché est positive.")
    elif opinion_score is not None and opinion_score < 50:
        weaknesses.append("L'opinion marché est mitigée ou négative.")

    if not strengths:
        strengths.append("Le projet dispose de signaux exploitables pour poursuivre la validation.")
    if not weaknesses:
        weaknesses.append("Les principaux risques doivent encore être précisés avec plus de données.")

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "interpretation": "Analyse générée à partir des scores existants, des facteurs explicatifs et des signaux marché.",
    }


def _fallback_recommendations(weaknesses: list[str]) -> list[str]:
    needs = map_weaknesses_to_needs(weaknesses, {})
    if not needs:
        return ["Collecter davantage de données terrain avant les décisions d'investissement."]
    return [f"Travailler le besoin prioritaire: {need}." for need in needs[:5]]


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _external_market_data_unavailable(market_analysis: dict[str, Any]) -> bool:
    features = market_analysis.get("features") or {}
    details = ((market_analysis.get("market_analysis") or {}).get("details") or {})
    inputs = details.get("input") or {}
    return features.get("search_trend_score") is None and inputs.get("search_trend_score") is None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
