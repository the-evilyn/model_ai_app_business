from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import csv
import json
import math
import urllib.parse
import urllib.request

import pandas as pd


WORLD_BANK_API_BASE = "https://api.worldbank.org/v2"

WORLD_BANK_INDICATORS = {
    "gdp_current_usd": "NY.GDP.MKTP.CD",
    "gdp_growth_percent": "NY.GDP.MKTP.KD.ZG",
    "population_total": "SP.POP.TOTL",
    "internet_users_percent": "IT.NET.USER.ZS",
    "services_value_added_percent_gdp": "NV.SRV.TOTL.ZS",
    "industry_value_added_percent_gdp": "NV.IND.TOTL.ZS",
    "manufacturing_value_added_percent_gdp": "NV.IND.MANF.ZS",
    "urban_population_percent": "SP.URB.TOTL.IN.ZS",
}

COUNTRY_ALIASES = {
    "morocco": "MAR",
    "maroc": "MAR",
    "france": "FRA",
    "united states": "USA",
    "usa": "USA",
    "us": "USA",
    "spain": "ESP",
    "espagne": "ESP",
    "germany": "DEU",
    "allemagne": "DEU",
    "canada": "CAN",
    "uk": "GBR",
    "united kingdom": "GBR",
    "tunisia": "TUN",
    "tunisie": "TUN",
    "algeria": "DZA",
    "algerie": "DZA",
    "egypt": "EGY",
    "egypte": "EGY",
}

SECTOR_GROUPS = {
    "ai": "services",
    "artificial intelligence": "services",
    "saas": "services",
    "software": "services",
    "fintech": "services",
    "ecommerce": "services",
    "e-commerce": "services",
    "education": "services",
    "edtech": "services",
    "health": "services",
    "healthcare": "services",
    "real estate": "services",
    "immobilier": "services",
    "restaurant": "services",
    "food": "services",
    "tourism": "services",
    "travel": "services",
    "manufacturing": "industry",
    "industrie": "industry",
    "climate": "industry",
    "energy": "industry",
    "construction": "industry",
    "agriculture": "agriculture",
}


@dataclass
class IndicatorValue:
    feature: str
    indicator_code: str
    value: float | None
    year: int | None
    source_url: str
    source_name: str = "World Bank Indicators API"


@dataclass
class MarketFeatureRecord:
    project_name: str
    sector: str
    country: str
    country_code: str
    keyword: str
    market_size_billion: float | None
    market_growth_rate_percent: float | None
    competition_level: str | None
    product_traction_users: int | None
    search_trend_score: float | None
    gdp_current_usd: float | None
    gdp_growth_percent: float | None
    population_total: float | None
    internet_users_percent: float | None
    services_value_added_percent_gdp: float | None
    industry_value_added_percent_gdp: float | None
    manufacturing_value_added_percent_gdp: float | None
    urban_population_percent: float | None
    estimated_sector_share_percent: float | None
    data_sources: str


class MarketDataCollector:
    """Collect real market signals before scoring market attractiveness.

    This class does not train a supervised model. It creates a traceable market
    feature dataset from public indicators and optional trend CSV files.
    """

    def __init__(self, timeout_seconds: int = 20) -> None:
        self.timeout_seconds = timeout_seconds

    def collect_project_features(
        self,
        project: dict[str, Any],
        google_trends_csv_path: str | Path | None = None,
        use_world_bank: bool = True,
    ) -> MarketFeatureRecord:
        country = str(project.get("country") or "Morocco")
        country_code = self.normalize_country_code(project.get("country_code") or country)
        sector = str(project.get("sector") or "Other")
        keyword = str(project.get("keyword") or sector)

        indicators = self.fetch_world_bank_context(country_code) if use_world_bank else {}
        trend_score = self.read_google_trends_score(google_trends_csv_path) if google_trends_csv_path else None

        gdp = self._indicator_value(indicators, "gdp_current_usd")
        gdp_growth = self._indicator_value(indicators, "gdp_growth_percent")
        sector_share = self.estimate_sector_share(sector, indicators)

        market_size_billion = self._to_float(project.get("market_size_billion"))
        if market_size_billion is None and gdp is not None and sector_share is not None:
            market_size_billion = (gdp * sector_share / 100) / 1_000_000_000

        market_growth = self._to_float(project.get("market_growth_rate_percent"))
        if market_growth is None:
            market_growth = gdp_growth

        sources = {
            "world_bank": [asdict(value) for value in indicators.values()],
            "google_trends_csv": str(google_trends_csv_path) if google_trends_csv_path else None,
            "user_inputs": {
                "competition_level": project.get("competition_level"),
                "product_traction_users": project.get("product_traction_users"),
                "market_size_billion": project.get("market_size_billion"),
                "market_growth_rate_percent": project.get("market_growth_rate_percent"),
            },
        }

        return MarketFeatureRecord(
            project_name=str(project.get("project_name") or project.get("title") or "Untitled project"),
            sector=sector,
            country=country,
            country_code=country_code,
            keyword=keyword,
            market_size_billion=self._round_or_none(market_size_billion),
            market_growth_rate_percent=self._round_or_none(market_growth),
            competition_level=self._competition_level(project),
            product_traction_users=self._to_int(project.get("product_traction_users")),
            search_trend_score=self._round_or_none(trend_score),
            gdp_current_usd=self._round_or_none(gdp),
            gdp_growth_percent=self._round_or_none(gdp_growth),
            population_total=self._round_or_none(self._indicator_value(indicators, "population_total")),
            internet_users_percent=self._round_or_none(self._indicator_value(indicators, "internet_users_percent")),
            services_value_added_percent_gdp=self._round_or_none(
                self._indicator_value(indicators, "services_value_added_percent_gdp")
            ),
            industry_value_added_percent_gdp=self._round_or_none(
                self._indicator_value(indicators, "industry_value_added_percent_gdp")
            ),
            manufacturing_value_added_percent_gdp=self._round_or_none(
                self._indicator_value(indicators, "manufacturing_value_added_percent_gdp")
            ),
            urban_population_percent=self._round_or_none(
                self._indicator_value(indicators, "urban_population_percent")
            ),
            estimated_sector_share_percent=self._round_or_none(sector_share),
            data_sources=json.dumps(sources, ensure_ascii=False),
        )

    def collect_dataset(
        self,
        projects: list[dict[str, Any]],
        output_path: str | Path = "data/market_signals_dataset.csv",
        use_world_bank: bool = True,
    ) -> pd.DataFrame:
        records = [
            asdict(self.collect_project_features(project, use_world_bank=use_world_bank))
            for project in projects
        ]
        df = pd.DataFrame(records)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output, index=False)
        return df

    def fetch_world_bank_context(self, country_code: str) -> dict[str, IndicatorValue]:
        context: dict[str, IndicatorValue] = {}
        for feature, indicator_code in WORLD_BANK_INDICATORS.items():
            context[feature] = self.fetch_world_bank_indicator(country_code, feature, indicator_code)
        return context

    def fetch_world_bank_indicator(
        self,
        country_code: str,
        feature: str,
        indicator_code: str,
    ) -> IndicatorValue:
        path = f"/country/{urllib.parse.quote(country_code)}/indicator/{urllib.parse.quote(indicator_code)}"
        query = urllib.parse.urlencode({"format": "json", "per_page": 80})
        url = f"{WORLD_BANK_API_BASE}{path}?{query}"

        try:
            with urllib.request.urlopen(url, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return IndicatorValue(feature=feature, indicator_code=indicator_code, value=None, year=None, source_url=url)

        rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
        for row in rows:
            value = self._to_float(row.get("value"))
            if value is not None:
                return IndicatorValue(
                    feature=feature,
                    indicator_code=indicator_code,
                    value=value,
                    year=self._to_int(row.get("date")),
                    source_url=url,
                )

        return IndicatorValue(feature=feature, indicator_code=indicator_code, value=None, year=None, source_url=url)

    def read_google_trends_score(self, path: str | Path) -> float | None:
        csv_path = Path(path)
        if not csv_path.exists():
            return None

        header_index = self._find_google_trends_header(csv_path)
        df = pd.read_csv(csv_path, skiprows=header_index)
        if df.empty:
            return None

        candidate_columns = [column for column in df.columns if str(column).lower() not in {"week", "month", "day", "date"}]
        if not candidate_columns:
            return None

        values = (
            df[candidate_columns[0]]
            .astype(str)
            .str.replace("<1", "0.5", regex=False)
            .str.replace(",", ".", regex=False)
        )
        numeric = pd.to_numeric(values, errors="coerce").dropna()
        if numeric.empty:
            return None
        return float(numeric.tail(min(12, len(numeric))).mean())

    def estimate_sector_share(
        self,
        sector: str,
        indicators: dict[str, IndicatorValue],
    ) -> float | None:
        group = SECTOR_GROUPS.get(self._clean(sector), "services")
        if group == "industry":
            return self._indicator_value(indicators, "industry_value_added_percent_gdp")
        if group == "agriculture":
            return 8.0
        return self._indicator_value(indicators, "services_value_added_percent_gdp")

    def normalize_country_code(self, value: Any) -> str:
        raw = str(value or "").strip()
        if len(raw) == 3 and raw.isalpha():
            return raw.upper()
        return COUNTRY_ALIASES.get(self._clean(raw), raw.upper()[:3] or "MAR")

    def _competition_level(self, project: dict[str, Any]) -> str | None:
        if project.get("competition_level"):
            return str(project["competition_level"]).lower()

        count = self._to_float(project.get("competition_count"))
        if count is None:
            return None
        if count < 10:
            return "low"
        if count < 50:
            return "medium"
        return "high"

    @staticmethod
    def _find_google_trends_header(path: Path) -> int:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            for index, row in enumerate(csv.reader(file)):
                if row and row[0].strip().lower() in {"week", "month", "day", "date"}:
                    return index
        return 0

    @staticmethod
    def _indicator_value(indicators: dict[str, IndicatorValue], feature: str) -> float | None:
        item = indicators.get(feature)
        return item.value if item else None

    @staticmethod
    def _clean(value: str) -> str:
        return " ".join(str(value).strip().lower().replace("_", " ").replace("-", " ").split())

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if math.isnan(number) or math.isinf(number):
            return None
        return number

    @staticmethod
    def _to_int(value: Any) -> int | None:
        number = MarketDataCollector._to_float(value)
        return int(number) if number is not None else None

    @staticmethod
    def _round_or_none(value: float | None, digits: int = 4) -> float | None:
        return round(value, digits) if value is not None else None


if __name__ == "__main__":
    collector = MarketDataCollector()
    example = collector.collect_project_features(
        {
            "project_name": "Real estate comparison platform",
            "sector": "real estate",
            "country": "Morocco",
            "keyword": "immobilier",
            "competition_level": "high",
            "product_traction_users": 12000,
        }
    )
    print(json.dumps(asdict(example), indent=2, ensure_ascii=False))
