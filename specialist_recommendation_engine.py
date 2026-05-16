from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import csv
import math
import re


DEFAULT_SPECIALIST_WEIGHTS = {
    "semantic_similarity": 0.40,
    "skills_match": 0.25,
    "sector_match": 0.15,
    "rating": 0.10,
    "availability": 0.05,
    "budget_language_location": 0.05,
}

AVAILABILITY_SCORES = {
    "available": 100.0,
    "disponible": 100.0,
    "soon": 65.0,
    "bientot disponible": 65.0,
    "bientôt disponible": 65.0,
    "busy": 35.0,
    "occupe": 35.0,
    "occupé": 35.0,
    "unavailable": 0.0,
    "indisponible": 0.0,
}

SYNONYM_GROUPS = [
    {"marketing", "growth", "go-to-market", "ads", "seo", "branding", "content", "social"},
    {"finance", "financial", "fundraising", "pricing", "unit economics", "business plan"},
    {"legal", "juridique", "contracts", "compliance", "privacy", "law"},
    {"ai", "ia", "machine learning", "nlp", "automation", "data"},
    {"ux", "ui", "design", "product discovery", "usability", "product"},
    {"market", "research", "competitor", "survey", "interviews", "sizing"},
    {"real estate", "immobilier", "housing", "houses", "property"},
    {"security", "cybersecurity", "risk", "audit", "cloud security"},
]


@dataclass
class ProjectRecommendationRequest:
    project_id: str | None
    title: str
    description: str
    sector: str
    needs: list[str] = field(default_factory=list)
    project_stage: str | None = None
    budget_per_hour: float | None = None
    preferred_language: str | None = None
    location: str | None = None
    top_k: int = 5


@dataclass
class SpecialistProfile:
    specialist_id: str
    full_name: str
    expertise_domain: str
    skills: list[str]
    sectors: list[str]
    industry_experience: int = 0
    hourly_rate: float = 0.0
    languages: list[str] = field(default_factory=list)
    location: str = ""
    average_rating: float = 0.0
    reviews_count: int = 0
    availability_status: str = "available"
    bio: str = ""
    completed_projects: int = 0


@dataclass
class SpecialistRecommendationResult:
    specialist_id: str
    full_name: str
    expertise_domain: str
    recommended_score: float
    reason: str
    score_details: dict[str, float]
    specialist: dict[str, Any]


class SpecialistRecommendationEngine:
    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = self._normalize_weights(weights or DEFAULT_SPECIALIST_WEIGHTS)

    def recommend(
        self,
        request: ProjectRecommendationRequest | dict[str, Any],
        specialists: list[SpecialistProfile | dict[str, Any]] | None = None,
        sample_csv_path: str | Path = "data/specialists_sample.csv",
    ) -> list[SpecialistRecommendationResult]:
        if isinstance(request, dict):
            request = ProjectRecommendationRequest(**request)

        specialist_profiles = self._normalize_specialists(
            specialists if specialists is not None else self.load_specialists_from_csv(sample_csv_path)
        )

        if not specialist_profiles:
            return []

        scored = [self._score_specialist(request, specialist) for specialist in specialist_profiles]
        scored.sort(key=lambda item: item.recommended_score, reverse=True)
        return scored[: max(int(request.top_k), 1)]

    def load_specialists_from_csv(self, path: str | Path) -> list[dict[str, Any]]:
        csv_path = Path(path)
        if not csv_path.exists():
            return []
        with csv_path.open("r", encoding="utf-8", newline="") as file:
            return list(csv.DictReader(file))

    def _score_specialist(
        self,
        request: ProjectRecommendationRequest,
        specialist: SpecialistProfile,
    ) -> SpecialistRecommendationResult:
        semantic_similarity = self._semantic_similarity_score(request, specialist)
        skills_match = self._skills_match_score(request.needs, specialist.skills, request.description)
        sector_match = self._sector_match_score(request.sector, specialist.sectors, specialist.bio)
        rating = self._rating_score(specialist.average_rating, specialist.reviews_count)
        availability = self._availability_score(specialist.availability_status)
        budget_language_location = self._budget_language_location_score(request, specialist)

        details = {
            "semantic_similarity": semantic_similarity,
            "skills_match": skills_match,
            "sector_match": sector_match,
            "rating": rating,
            "availability": availability,
            "budget_language_location": budget_language_location,
        }

        final_score = sum(self.weights[key] * details[key] for key in self.weights)
        reason = self._build_reason(request, specialist, details)

        return SpecialistRecommendationResult(
            specialist_id=specialist.specialist_id,
            full_name=specialist.full_name,
            expertise_domain=specialist.expertise_domain,
            recommended_score=round(self._bounded(final_score), 2),
            reason=reason,
            score_details={key: round(value, 2) for key, value in details.items()},
            specialist=asdict(specialist),
        )

    def _semantic_similarity_score(
        self,
        request: ProjectRecommendationRequest,
        specialist: SpecialistProfile,
    ) -> float:
        project_text = " ".join(
            [
                request.title,
                request.description,
                request.sector,
                request.project_stage or "",
                " ".join(request.needs),
            ]
        )
        specialist_text = " ".join(
            [
                specialist.expertise_domain,
                specialist.bio,
                " ".join(specialist.skills),
                " ".join(specialist.sectors),
            ]
        )
        return self._token_cosine(project_text, specialist_text) * 100

    def _skills_match_score(self, needs: list[str], skills: list[str], description: str) -> float:
        expanded_needs = self._expand_terms(needs + self._extract_need_terms(description))
        expanded_skills = self._expand_terms(skills)

        if not expanded_needs:
            return 55.0

        matched = len(expanded_needs & expanded_skills)
        return self._bounded((matched / max(len(expanded_needs), 1)) * 100)

    def _sector_match_score(self, project_sector: str, specialist_sectors: list[str], specialist_bio: str) -> float:
        project_tokens = self._expand_terms([project_sector])
        specialist_tokens = self._expand_terms(specialist_sectors + [specialist_bio])

        if project_tokens & specialist_tokens:
            return 100.0

        project_clean = self._clean_text(project_sector)
        if project_clean in {"other", "unknown", ""}:
            return 55.0
        return 25.0

    def _rating_score(self, average_rating: float, reviews_count: int) -> float:
        rating_component = self._bounded(float(average_rating) / 5 * 100)
        review_confidence = min(math.log1p(max(int(reviews_count), 0)) / math.log1p(50), 1.0)
        return self._bounded((0.75 * rating_component) + (0.25 * review_confidence * 100))

    def _availability_score(self, status: str) -> float:
        return AVAILABILITY_SCORES.get(self._clean_text(status), 50.0)

    def _budget_language_location_score(
        self,
        request: ProjectRecommendationRequest,
        specialist: SpecialistProfile,
    ) -> float:
        parts = []

        if request.budget_per_hour is not None and request.budget_per_hour > 0:
            if specialist.hourly_rate <= request.budget_per_hour:
                parts.append(100.0)
            else:
                over_budget_ratio = specialist.hourly_rate / request.budget_per_hour
                parts.append(self._bounded(100 - (over_budget_ratio - 1) * 100))

        if request.preferred_language:
            language = self._clean_text(request.preferred_language)
            specialist_languages = {self._clean_text(value) for value in specialist.languages}
            parts.append(100.0 if language in specialist_languages else 35.0)

        if request.location:
            request_location = self._clean_text(request.location)
            specialist_location = self._clean_text(specialist.location)
            parts.append(100.0 if request_location and request_location in specialist_location else 60.0)

        if not parts:
            return 60.0
        return sum(parts) / len(parts)

    def _build_reason(
        self,
        request: ProjectRecommendationRequest,
        specialist: SpecialistProfile,
        details: dict[str, float],
    ) -> str:
        reasons = []
        if details["semantic_similarity"] >= 45:
            reasons.append("profil proche de la description du projet")
        if details["skills_match"] >= 50:
            reasons.append("competences adaptees aux besoins")
        if details["sector_match"] >= 80:
            reasons.append("experience dans le secteur")
        if details["rating"] >= 80:
            reasons.append("bonne evaluation")
        if details["availability"] >= 80:
            reasons.append("disponible")

        if not reasons:
            reasons.append("profil partiellement compatible")

        return f"{specialist.full_name} est recommande(e) pour: " + ", ".join(reasons) + "."

    def _normalize_specialists(
        self,
        specialists: list[SpecialistProfile | dict[str, Any]],
    ) -> list[SpecialistProfile]:
        normalized = []
        for item in specialists:
            if isinstance(item, SpecialistProfile):
                normalized.append(item)
                continue

            normalized.append(
                SpecialistProfile(
                    specialist_id=str(item.get("specialist_id") or item.get("id") or ""),
                    full_name=str(item.get("full_name") or item.get("fullName") or ""),
                    expertise_domain=str(item.get("expertise_domain") or item.get("expertiseDomain") or item.get("profession") or ""),
                    skills=self._split_multi_value(item.get("skills", "")),
                    sectors=self._split_multi_value(item.get("sectors", item.get("sector", ""))),
                    industry_experience=int(float(item.get("industry_experience") or item.get("industryExperience") or item.get("experienceYears") or 0)),
                    hourly_rate=float(item.get("hourly_rate") or item.get("hourlyRate") or 0),
                    languages=self._split_multi_value(item.get("languages", "")),
                    location=str(item.get("location", "")),
                    average_rating=float(item.get("average_rating") or item.get("averageRating") or item.get("rating") or 0),
                    reviews_count=int(float(item.get("reviews_count") or item.get("reviewsCount") or 0)),
                    availability_status=str(item.get("availability_status") or item.get("availabilityStatus") or "available"),
                    bio=str(item.get("bio", "")),
                    completed_projects=int(float(item.get("completed_projects") or item.get("completedProjects") or 0)),
                )
            )
        return [item for item in normalized if item.specialist_id and item.full_name]

    @staticmethod
    def _split_multi_value(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [part.strip() for part in re.split(r"[;,|]", str(value)) if part.strip()]

    def _extract_need_terms(self, text: str) -> list[str]:
        clean = self._clean_text(text)
        terms = []
        for group in SYNONYM_GROUPS:
            for word in group:
                if word in clean:
                    terms.append(word)
        return terms

    def _expand_terms(self, terms: list[str]) -> set[str]:
        expanded = set()
        for term in terms:
            clean = self._clean_text(term)
            if not clean:
                continue
            expanded.add(clean)
            for group in SYNONYM_GROUPS:
                if clean in group or any(item in clean for item in group):
                    expanded.update(group)
        return expanded

    def _token_cosine(self, left: str, right: str) -> float:
        left_counts = self._token_counts(left)
        right_counts = self._token_counts(right)
        if not left_counts or not right_counts:
            return 0.0

        common_tokens = set(left_counts) & set(right_counts)
        dot = sum(left_counts[token] * right_counts[token] for token in common_tokens)
        left_norm = math.sqrt(sum(value * value for value in left_counts.values()))
        right_norm = math.sqrt(sum(value * value for value in right_counts.values()))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)

    def _token_counts(self, text: str) -> dict[str, int]:
        tokens = re.findall(r"[a-zA-Z0-9]+", self._clean_text(text))
        expanded = []
        for token in tokens:
            expanded.append(token)
            for group in SYNONYM_GROUPS:
                if token in group:
                    expanded.extend(group)
        counts: dict[str, int] = {}
        for token in expanded:
            counts[token] = counts.get(token, 0) + 1
        return counts

    @staticmethod
    def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
        total = sum(max(float(value), 0.0) for value in weights.values())
        if total <= 0:
            return DEFAULT_SPECIALIST_WEIGHTS.copy()
        return {key: max(float(value), 0.0) / total for key, value in weights.items()}

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", str(value).lower().strip())

    @staticmethod
    def _bounded(value: float, low: float = 0.0, high: float = 100.0) -> float:
        if math.isnan(value) or math.isinf(value):
            return 50.0
        return max(low, min(high, float(value)))


def recommend_specialists(payload: dict[str, Any], specialists: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    engine = SpecialistRecommendationEngine()
    return [asdict(item) for item in engine.recommend(payload, specialists=specialists)]


if __name__ == "__main__":
    example = {
        "project_id": "p_001",
        "title": "AI business validation platform",
        "description": "A SaaS platform that uses AI, sentiment analysis and market research to validate startup ideas.",
        "sector": "SaaS",
        "needs": ["AI", "market research", "go-to-market", "business plan"],
        "project_stage": "idea",
        "budget_per_hour": 65,
        "preferred_language": "fr",
        "location": "Morocco",
        "top_k": 3,
    }
    for recommendation in recommend_specialists(example):
        print(recommendation)
