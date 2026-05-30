from __future__ import annotations

from dataclasses import asdict
from typing import Any

from business_validation_score_engine import (
    DEFAULT_STARTUP_FEATURES,
    BusinessValidationRequest,
    BusinessValidationScoreEngine,
)


FEATURE_LABELS = {
    "product_traction_users": "Traction utilisateur",
    "market_size_billion": "Taille du marché",
    "burn_to_revenue_ratio": "Ratio dépenses / revenus",
    "revenue_million": "Revenus",
    "founder_experience_years": "Expérience du fondateur",
    "funding_rounds": "Tours de financement",
    "team_size": "Taille de l'équipe",
    "burn_rate_million": "Dépenses mensuelles",
    "traction_per_employee": "Traction par employé",
    "sector": "Secteur",
    "investor_type": "Type d'investisseur",
    "founder_background": "Profil du fondateur",
    "investor_type_angel": "Investisseur angel",
    "investor_type_none": "Aucun investisseur",
    "investor_type_tier1_vc": "Investisseur VC tier 1",
    "investor_type_tier2_vc": "Investisseur VC tier 2",
    "founder_background_academic": "Fondateur académique",
    "founder_background_ex_bigtech": "Fondateur ex-Big Tech",
    "founder_background_first_time": "Fondateur first-time",
    "founder_background_serial_founder": "Fondateur serial entrepreneur",
}


class StartupInterpretabilityEngine:
    def __init__(self, score_engine: BusinessValidationScoreEngine) -> None:
        self.score_engine = score_engine

    def explain(
        self,
        request: BusinessValidationRequest,
        startup_model_sector: str,
        top_k: int = 3,
    ) -> dict[str, Any]:
        pipeline = self.score_engine._extract_pipeline(self.score_engine.startup_artifact)
        if pipeline is None:
            return self._fallback_explanation(request, "SHAP unavailable: startup model is not loaded.")

        feature_order = self.score_engine._artifact_value(
            "train_columns_after_filtering",
            DEFAULT_STARTUP_FEATURES,
        )
        try:
            input_df = self.score_engine._prepare_startup_input(
                request,
                startup_model_sector,
                feature_order,
            )
            shap_result = self._compute_shap_values(pipeline, input_df)
            if shap_result is None:
                raise RuntimeError(
                    "the loaded pipeline could not be decomposed into preprocessor, selector and final model"
                )
            shap_values, feature_names, transformed_row = shap_result
            impacts = self._feature_impacts(input_df, shap_values, feature_names, transformed_row)
            return self._build_response(request, impacts, top_k=top_k)
        except Exception as exc:
            return self._fallback_explanation(request, f"SHAP unavailable: {exc}")

    def _compute_shap_values(self, pipeline: Any, input_df: Any) -> tuple[Any, list[str], Any] | None:
        try:
            import numpy as np
        except Exception as exc:
            raise RuntimeError("numpy is required for SHAP explanations") from exc

        if not hasattr(pipeline, "named_steps"):
            return None

        preprocessor = pipeline.named_steps.get("preprocessor")
        selector = pipeline.named_steps.get("selector")
        model = pipeline.named_steps.get("model")
        if preprocessor is None or model is None:
            return None

        transformed = preprocessor.transform(input_df)
        all_feature_names = list(preprocessor.get_feature_names_out())

        if selector is not None:
            selected = selector.transform(transformed)
            if hasattr(selector, "get_support"):
                selected_feature_names = [
                    name for name, keep in zip(all_feature_names, selector.get_support()) if keep
                ]
            else:
                selected_feature_names = self.score_engine._artifact_value(
                    "selected_transformed_features",
                    all_feature_names,
                )
        else:
            selected = transformed
            selected_feature_names = all_feature_names

        selected_array = selected.toarray() if hasattr(selected, "toarray") else selected
        selected_array = np.asarray(selected_array)
        transformed_row = selected_array[0]

        values = self._xgboost_shap_values(model, selected_array, selected_feature_names)
        if values is None:
            values = self._python_shap_values(model, selected_array)
        if values is None:
            raise RuntimeError("neither XGBoost TreeSHAP nor python shap could explain the final model")

        return values, selected_feature_names, transformed_row

    @staticmethod
    def _xgboost_shap_values(model: Any, selected_array: Any, feature_names: list[str]) -> Any | None:
        try:
            import xgboost as xgb

            booster = model.get_booster()
            matrix = xgb.DMatrix(selected_array, feature_names=feature_names)
            contributions = booster.predict(matrix, pred_contribs=True)
            return contributions[0][:-1]
        except Exception:
            return None

    @staticmethod
    def _python_shap_values(model: Any, selected_array: Any) -> Any | None:
        try:
            import numpy as np
            import shap

            explainer = shap.TreeExplainer(model)
            explanation = explainer.shap_values(selected_array)
            values = explanation[-1] if isinstance(explanation, list) else explanation
            values = np.asarray(values)
            if values.ndim == 3:
                return values[0, :, -1]
            if values.ndim == 2:
                return values[0]
            return values
        except Exception:
            return None

    def _feature_impacts(
        self,
        input_df: Any,
        shap_values: Any,
        feature_names: list[str],
        transformed_row: Any,
    ) -> list[dict[str, Any]]:
        row = input_df.iloc[0].to_dict()
        impacts = []
        for index, feature in enumerate(feature_names):
            impact = float(shap_values[index])
            raw_feature = self._raw_feature_name(feature)
            raw_value = self._display_value(feature, raw_feature, row, transformed_row[index])
            impacts.append(
                {
                    "feature": raw_feature,
                    "label": FEATURE_LABELS.get(raw_feature, raw_feature.replace("_", " ").title()),
                    "value": raw_value,
                    "impact": round(impact, 4),
                    "interpretation": self._interpret(raw_feature, impact),
                }
            )
        return impacts

    @staticmethod
    def _raw_feature_name(transformed_feature: str) -> str:
        feature = transformed_feature
        if "__" in feature:
            feature = feature.split("__", 1)[1]
        for prefix in ("investor_type_", "sector_", "founder_background_"):
            if feature.startswith(prefix):
                return feature
        return feature

    @staticmethod
    def _display_value(
        transformed_feature: str,
        raw_feature: str,
        row: dict[str, Any],
        transformed_value: Any,
    ) -> Any:
        feature = transformed_feature.split("__", 1)[1] if "__" in transformed_feature else transformed_feature
        for prefix, original in (
            ("investor_type_", "investor_type"),
            ("sector_", "sector"),
            ("founder_background_", "founder_background"),
        ):
            if feature.startswith(prefix):
                category = feature.removeprefix(prefix)
                return {
                    "category": category,
                    "active": bool(round(float(transformed_value))),
                    "input": row.get(original),
                }
        return row.get(raw_feature)

    def _build_response(
        self,
        request: BusinessValidationRequest,
        impacts: list[dict[str, Any]],
        top_k: int,
    ) -> dict[str, Any]:
        positives = sorted(
            [item for item in impacts if item["impact"] > 0],
            key=lambda item: item["impact"],
            reverse=True,
        )[:top_k]
        negatives = sorted(
            [item for item in impacts if item["impact"] < 0],
            key=lambda item: item["impact"],
        )[:top_k]
        return {
            "method": "SHAP",
            "positiveFactors": positives,
            "negativeFactors": negatives,
            "fallback": False,
            "inputSnapshot": asdict(request),
        }

    def _fallback_explanation(self, request: BusinessValidationRequest, reason: str) -> dict[str, Any]:
        safe_revenue = self.score_engine._normalize_revenue_for_training(request.revenue_million)
        burn_to_revenue = float(request.burn_rate_million) / safe_revenue
        positives = []
        negatives = []

        if request.product_traction_users >= 1000:
            positives.append(self._factor("product_traction_users", request.product_traction_users, 0.0, True))
        else:
            negatives.append(self._factor("product_traction_users", request.product_traction_users, 0.0, False))
        if request.market_size_billion >= 1:
            positives.append(self._factor("market_size_billion", request.market_size_billion, 0.0, True))
        if burn_to_revenue > 0.000001:
            negatives.append(self._factor("burn_to_revenue_ratio", round(burn_to_revenue, 4), 0.0, False))
        if request.founder_experience_years >= 3:
            positives.append(self._factor("founder_experience_years", request.founder_experience_years, 0.0, True))

        return {
            "method": "fallback_feature_rules",
            "positiveFactors": positives[:3],
            "negativeFactors": negatives[:3],
            "fallback": True,
            "warning": reason,
            "inputSnapshot": asdict(request),
        }

    def _factor(self, feature: str, value: Any, impact: float, positive: bool) -> dict[str, Any]:
        return {
            "feature": feature,
            "label": FEATURE_LABELS.get(feature, feature.replace("_", " ").title()),
            "value": value,
            "impact": impact,
            "interpretation": self._interpret(feature, impact if positive else -abs(impact)),
        }

    @staticmethod
    def _interpret(feature: str, impact: float) -> str:
        label = FEATURE_LABELS.get(feature, feature.replace("_", " "))
        direction = "positivement" if impact >= 0 else "négativement"
        if feature == "burn_to_revenue_ratio":
            quality = "favorable" if impact >= 0 else "défavorable"
            return f"Un ratio dépenses / revenus {quality} contribue {direction} à la prédiction."
        if feature == "burn_rate_million":
            quality = "maîtrisées" if impact >= 0 else "élevées"
            return f"Des dépenses mensuelles {quality} contribuent {direction} à la prédiction."
        if feature in ("product_traction_users", "traction_per_employee"):
            quality = "solide" if impact >= 0 else "insuffisante"
            return f"Une traction utilisateur {quality} contribue {direction} à la prédiction."
        if feature == "founder_experience_years":
            quality = "forte" if impact >= 0 else "limitée"
            return f"Une expérience fondateur {quality} contribue {direction} à la prédiction."
        if feature == "market_size_billion":
            quality = "important" if impact >= 0 else "limité"
            return f"Un marché {quality} contribue {direction} à la prédiction."
        if impact >= 0:
            return f"{label} contribue positivement à la prédiction."
        return f"{label} contribue négativement à la prédiction."
