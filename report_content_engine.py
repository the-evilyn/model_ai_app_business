from __future__ import annotations

import json
from typing import Any

from llm_client import generate_json_response, get_llm_provider


REPORT_KEYS = {
    "title": "Rapport de validation business",
    "executiveSummary": "",
    "analysisSummary": "",
    "strengths": [],
    "weaknesses": [],
    "recommendations": [],
    "businessPlan": {
        "problem": "",
        "solution": "",
        "targetCustomers": "",
        "valueProposition": "",
        "businessModel": "",
        "marketingStrategy": "",
        "risks": "",
        "nextSteps": "",
    },
    "warnings": [],
}


def generate_report_content(
    project_data: dict[str, Any],
    analysis_result: dict[str, Any],
    include_business_plan: bool = True,
) -> dict[str, Any]:
    system_prompt = """
Tu génères un contenu de rapport de validation business.
Les scores fournis sont définitifs: ne les modifie jamais, ne les recalcule jamais.
Retourne uniquement un JSON valide avec les clés demandées.
Le business plan doit être court, concret et cohérent avec les faiblesses et recommandations.
"""
    payload = {
        "project": project_data,
        "analysisResult": analysis_result,
        "includeBusinessPlan": include_business_plan,
        "expectedSchema": REPORT_KEYS,
    }
    response = generate_json_response(system_prompt, json.dumps(payload, ensure_ascii=False))
    parsed = response.get("json") or {}
    report = _fallback_report(project_data, analysis_result, include_business_plan)
    report.update({key: parsed[key] for key in parsed if key in report})
    report["warnings"] = analysis_result.get("warnings", report.get("warnings", []))
    if not include_business_plan:
        report["businessPlan"] = {}
    report["generationSource"] = (
        f"{get_llm_provider()['provider']}_llm"
        if get_llm_provider()["configured"]
        else "fallback_rules"
    )
    return report


def _fallback_report(
    project_data: dict[str, Any],
    analysis_result: dict[str, Any],
    include_business_plan: bool,
) -> dict[str, Any]:
    strengths = analysis_result.get("strengths", [])
    weaknesses = analysis_result.get("weaknesses", [])
    recommendations = analysis_result.get("recommendations", [])
    title = f"Rapport de validation business - {project_data.get('project_name') or project_data.get('title') or 'Projet'}"
    report = {
        "title": title,
        "executiveSummary": "Synthèse générée à partir de l'analyse IA disponible.",
        "analysisSummary": analysis_result.get("interpretation", ""),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations,
        "businessPlan": {
            "problem": project_data.get("problem", ""),
            "solution": project_data.get("project_description", ""),
            "targetCustomers": project_data.get("target_customers", ""),
            "valueProposition": project_data.get("value_proposition", ""),
            "businessModel": project_data.get("business_model", ""),
            "marketingStrategy": "Prioriser les canaux liés aux besoins générés.",
            "risks": "; ".join(weaknesses[:3]),
            "nextSteps": "; ".join(recommendations[:3]),
        }
        if include_business_plan
        else {},
        "warnings": analysis_result.get("warnings", []),
    }
    return report
