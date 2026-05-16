
from __future__ import annotations

from typing import Any

import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="NexusAI API Tester",
    page_icon=":satellite:",
    layout="wide",
)


def post_json(api_base_url: str, endpoint: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    url = f"{api_base_url.rstrip('/')}{endpoint}"
    try:
        response = requests.post(url, json=payload, timeout=90)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"Erreur API: {exc}")
        return None


def get_json(api_base_url: str, endpoint: str) -> dict[str, Any] | None:
    url = f"{api_base_url.rstrip('/')}{endpoint}"
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"Erreur API: {exc}")
        return None


def show_json_response(data: dict[str, Any] | None) -> None:
    if data is not None:
        st.json(data)


def render_project_payload_form(form_key: str) -> tuple[bool, dict[str, Any]]:
    with st.form(form_key):
        col1, col2, col3 = st.columns(3)

        with col1:
            project_name = st.text_input("Nom du projet", "NexusAI Business Validator", key=f"{form_key}_name")
            sector = st.text_input("Secteur", "SaaS", key=f"{form_key}_sector")
            project_description = st.text_area(
                "Description du projet",
                "A SaaS platform that uses AI, market data and sentiment analysis to validate startup ideas.",
                height=130,
                key=f"{form_key}_description",
            )
            country = st.text_input("Pays", "Morocco", key=f"{form_key}_country")
            keyword = st.text_input("Mot-cle marche", "business validation", key=f"{form_key}_keyword")

        with col2:
            funding_rounds = st.number_input("Tours de financement", 1, 20, 1, key=f"{form_key}_rounds")
            founder_experience_years = st.number_input(
                "Experience fondateur (annees)", 0.0, 40.0, 5.0, key=f"{form_key}_experience"
            )
            team_size = st.number_input("Taille equipe", 1, 5000, 8, key=f"{form_key}_team")
            market_size_billion = st.number_input(
                "Taille marche manuelle (milliards)", 0.0, 500.0, 25.0, key=f"{form_key}_market_size"
            )
            product_traction_users = st.number_input(
                "Traction utilisateurs", 0, 50_000_000, 12000, key=f"{form_key}_traction"
            )

        with col3:
            burn_rate_million = st.number_input("Burn rate (millions)", 0.0, 500.0, 0.8, key=f"{form_key}_burn")
            revenue_million = st.number_input(
                "Revenue annuel (millions)",
                0.000001,
                5_000_000.0,
                0.3,
                help="Exemple: 0.3 = 300 000. L'API convertit cette valeur vers l'echelle du dataset d'entrainement.",
                key=f"{form_key}_revenue",
            )
            market_growth_rate_percent = st.number_input(
                "Croissance marche manuelle (%)", -20.0, 100.0, 8.0, key=f"{form_key}_growth"
            )
            competition_level = st.selectbox("Concurrence", ["low", "medium", "high"], index=1, key=f"{form_key}_comp")
            search_trend_score = st.slider("Trend score manuel", 0, 100, 65, key=f"{form_key}_trend")

        col4, col5, col6 = st.columns(3)
        with col4:
            investor_type = st.selectbox(
                "Type investisseur",
                ["none", "angel", "tier1_vc", "tier2_vc"],
                index=1,
                key=f"{form_key}_investor",
            )
        with col5:
            founder_background = st.selectbox(
                "Profil fondateur",
                ["first_time", "serial_founder", "ex_bigtech", "academic"],
                index=0,
                key=f"{form_key}_background",
            )
        with col6:
            use_world_bank = st.checkbox("Enrichir avec World Bank", value=True, key=f"{form_key}_worldbank")

        opinions_text = st.text_area(
            "Opinions marche / clients, une phrase par ligne",
            "Customers like the idea because validation is difficult.\nSome users complain that consulting is expensive.",
            height=100,
            key=f"{form_key}_opinions",
        )

        submitted = st.form_submit_button("Envoyer a l'API")

    opinions = [line.strip() for line in opinions_text.splitlines() if line.strip()]
    payload = {
        "project_name": project_name,
        "project_description": project_description,
        "sector": sector,
        "funding_rounds": funding_rounds,
        "founder_experience_years": founder_experience_years,
        "team_size": team_size,
        "market_size_billion": market_size_billion,
        "product_traction_users": product_traction_users,
        "burn_rate_million": burn_rate_million,
        "revenue_million": revenue_million,
        "investor_type": investor_type,
        "founder_background": founder_background,
        "market_growth_rate_percent": market_growth_rate_percent,
        "competition_level": competition_level,
        "search_trend_score": search_trend_score,
        "country": country,
        "keyword": keyword,
        "use_world_bank": use_world_bank,
        "opinions": opinions,
    }
    return submitted, payload


st.title("NexusAI - Test des APIs IA")
st.caption("Cette interface Streamlit appelle FastAPI. Elle ne charge pas directement les modeles.")

with st.sidebar:
    api_base_url = st.text_input("FastAPI base URL", "http://127.0.0.1:8001")
    st.code("uvicorn business_validation_api:app --reload --port 8001", language="bash")
    st.code("streamlit run streamlit_api_app.py", language="bash")
    if st.button("Tester /health"):
        show_json_response(get_json(api_base_url, "/health"))


tabs = st.tabs(
    [
        "Statut API",
        "Startup Success",
        "Sentiment",
        "Market Analysis",
        "Specialistes",
        "Score final",
    ]
)


with tabs[0]:
    st.subheader("Statut des modeles")
    status = get_json(api_base_url, "/api/v1/models/status")
    if status:
        rows = []
        for module, info in status.items():
            rows.append(
                {
                    "module": module,
                    "loaded": info.get("loaded"),
                    "fallback": info.get("fallback", False),
                    "type/source": info.get("type") or info.get("source") or info.get("artifact_path"),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        st.json(status)


with tabs[1]:
    st.subheader("API Startup Success")
    submitted, payload = render_project_payload_form("startup_api")
    if submitted:
        startup_payload = {
            key: payload[key]
            for key in [
                "project_name",
                "project_description",
                "sector",
                "funding_rounds",
                "founder_experience_years",
                "team_size",
                "market_size_billion",
                "product_traction_users",
                "burn_rate_million",
                "revenue_million",
                "investor_type",
                "founder_background",
            ]
        }
        data = post_json(api_base_url, "/api/v1/startup-success/predict", startup_payload)
        if data:
            st.metric("Probabilite de succes", f"{data['success_probability']:.2f}%")
            st.write("Prediction:", data["prediction_label"])
            st.write("Modele:", data["model_mode"])
        show_json_response(data)


with tabs[2]:
    st.subheader("API Sentiment Analysis")
    texts = st.text_area(
        "Textes a analyser",
        "Customers love this product and the market demand is growing.\nUsers complain about high prices and poor service.\nThe idea is interesting but the market is uncertain.",
        height=160,
    )
    if st.button("Analyser les sentiments"):
        payload = {"texts": [line.strip() for line in texts.splitlines() if line.strip()]}
        data = post_json(api_base_url, "/api/v1/sentiment/analyze", payload)
        if data:
            st.metric("Score sentiment moyen", f"{data['average_sentiment_score']:.2f}%")
            st.write("Label global:", data["overall_label"])
            st.write("Modele:", data["model_mode"])
            st.dataframe(pd.DataFrame(data["results"]), use_container_width=True)
        show_json_response(data)


with tabs[3]:
    st.subheader("API Market Analysis")
    with st.form("market_api_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            project_name = st.text_input("Nom projet", "Real estate comparison platform")
            sector = st.text_input("Secteur", "real estate")
            country = st.text_input("Pays", "Morocco")
            country_code = st.text_input("Code pays ISO3", "MAR")
            keyword = st.text_input("Mot-cle", "immobilier")
        with col2:
            use_world_bank = st.checkbox("Collecter World Bank", value=True)
            competition_level = st.selectbox("Concurrence", ["low", "medium", "high"], index=2)
            product_traction_users = st.number_input("Traction utilisateurs", 0, 50_000_000, 12000)
            search_trend_score = st.slider("Trend score manuel", 0, 100, 65)
        with col3:
            market_size_billion = st.number_input("Taille marche manuelle", 0.0, 500.0, 0.0)
            market_growth_rate_percent = st.number_input("Croissance manuelle (%)", -20.0, 100.0, 0.0)
            google_trends_csv_path = st.text_input("CSV Google Trends optionnel", "")
        submit_market = st.form_submit_button("Analyser le marche")

    if submit_market:
        payload = {
            "project_name": project_name,
            "sector": sector,
            "country": country,
            "country_code": country_code,
            "keyword": keyword,
            "competition_level": competition_level,
            "product_traction_users": product_traction_users,
            "search_trend_score": search_trend_score,
            "use_world_bank": use_world_bank,
        }
        if market_size_billion > 0:
            payload["market_size_billion"] = market_size_billion
        if market_growth_rate_percent != 0:
            payload["market_growth_rate_percent"] = market_growth_rate_percent
        if google_trends_csv_path.strip():
            payload["google_trends_csv_path"] = google_trends_csv_path.strip()

        data = post_json(api_base_url, "/api/v1/market-analysis/score", payload)
        if data:
            market = data["market_analysis"]
            st.metric("Market Score", f"{market['market_score']:.2f}%")
            st.write("Label:", market["market_label"])
            st.dataframe(pd.DataFrame([market["sub_scores"]]), use_container_width=True)
            st.write("Features collectees:")
            st.dataframe(pd.DataFrame([data["features"]]), use_container_width=True)
        show_json_response(data)


with tabs[4]:
    st.subheader("API Recommandation Specialistes")
    with st.form("specialist_api_form"):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Titre projet", "AI business validation platform")
            sector = st.text_input("Secteur projet", "SaaS")
            description = st.text_area(
                "Description",
                "A SaaS platform that uses AI, sentiment analysis and market research to validate startup ideas.",
                height=140,
            )
        with col2:
            needs = st.multiselect(
                "Besoins",
                ["AI", "market research", "go-to-market", "business plan", "legal", "finance", "UX", "cybersecurity"],
                default=["AI", "market research", "go-to-market"],
            )
            budget = st.number_input("Budget par heure", 0.0, 500.0, 65.0)
            language = st.selectbox("Langue preferee", ["fr", "en", "ar"], index=0)
            location = st.text_input("Localisation", "Morocco")
            top_k = st.slider("Nombre de specialistes", 1, 10, 5)
        submit_specialist = st.form_submit_button("Recommander")

    if submit_specialist:
        payload = {
            "title": title,
            "description": description,
            "sector": sector,
            "needs": needs,
            "budget_per_hour": budget,
            "preferred_language": language,
            "location": location,
            "top_k": top_k,
        }
        data = post_json(api_base_url, "/api/v1/specialists/recommend", payload)
        if data:
            rows = []
            for item in data["recommendations"]:
                rows.append(
                    {
                        "specialist": item["full_name"],
                        "domain": item["expertise_domain"],
                        "score": item["recommended_score"],
                        "reason": item["reason"],
                    }
                )
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        show_json_response(data)


with tabs[5]:
    st.subheader("API Score Final Business Validation")
    submitted, payload = render_project_payload_form("final_api")
    if submitted:
        payload["specialist_match_score"] = 70
        payload["risk_score"] = 35
        data = post_json(api_base_url, "/api/v1/business-validation/score", payload)
        if data:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Score final", f"{data['final_score']:.2f}%")
            col2.metric("Startup", f"{data['startup_success_score']:.2f}%")
            col3.metric("Sentiment", f"{data['market_sentiment_score']:.2f}%")
            col4.metric("Marche", f"{data['market_analysis_score']:.2f}%")
            st.write("Label:", data["final_label"])
            if data.get("warnings"):
                st.warning(" | ".join(data["warnings"]))
        show_json_response(data)
