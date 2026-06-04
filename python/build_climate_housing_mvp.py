from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from build_future_reports import build_html_document, export_pdf, fmt
from config import ensure_directories, load_config, resolve_path
from db import connect, run_sql_file


MAINE_COUNTIES = {
    "001": "Androscoggin",
    "003": "Aroostook",
    "005": "Cumberland",
    "007": "Franklin",
    "009": "Hancock",
    "011": "Kennebec",
    "013": "Knox",
    "015": "Lincoln",
    "017": "Oxford",
    "019": "Penobscot",
    "021": "Piscataquis",
    "023": "Sagadahoc",
    "025": "Somerset",
    "027": "Waldo",
    "029": "Washington",
    "031": "York",
}


@dataclass
class ClimateHousingTown:
    town: str
    county: str
    acs_year: int
    acs_population: int
    median_household_income: float
    pct_below_poverty: float
    pct_zero_vehicle_households: float
    pct_65_plus: float
    pct_with_disability: float
    pct_under_18: float
    pct_cost_burdened_households: float
    pct_cost_burdened_renter_households: float
    pct_cost_burdened_owner_households: float
    pct_vacant_housing_units: float
    pct_seasonal_housing_units: float
    pct_long_commute_workers: float
    pct_work_from_home_workers: float
    pct_no_internet_or_subscription_households: float
    housing_need_score: float = 0
    social_vulnerability_score: float = 0
    infrastructure_efficiency_proxy_score: float = 0
    resilience_investment_priority_score: float = 0
    climate_safe_housing_mvp_score: float = 0
    mvp_priority_lane: str = ""
    key_drivers: list[str] = field(default_factory=list)


def value(row: dict[str, Any], key: str, default: Any = 0) -> Any:
    result = row.get(key, default)
    if isinstance(result, Decimal):
        return float(result)
    return result if result is not None else default


def clamp(value_: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value_))


def normalize(value_: float, values: list[float]) -> float:
    low = min(values)
    high = max(values)
    if high == low:
        return 50.0
    return (value_ - low) / (high - low) * 100


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(lines)


def rows(cfg: dict[str, Any], sql: str) -> list[dict[str, Any]]:
    with connect(cfg) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = [description.name for description in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def fetch_towns(cfg: dict[str, Any]) -> list[ClimateHousingTown]:
    data = rows(cfg, """
        SELECT
            town,
            county_fips,
            acs_year,
            total_population,
            median_household_income,
            pct_below_poverty,
            pct_zero_vehicle_households,
            pct_65_plus,
            pct_with_disability,
            pct_under_18,
            pct_cost_burdened_households,
            pct_cost_burdened_renter_households,
            pct_cost_burdened_owner_households,
            pct_vacant_housing_units,
            pct_seasonal_housing_units,
            pct_long_commute_workers,
            pct_work_from_home_workers,
            pct_no_internet_or_subscription_households
        FROM acs_town_demographics
        WHERE total_population IS NOT NULL
          AND total_population > 0
        ORDER BY town, county_fips;
    """)
    towns = [
        ClimateHousingTown(
            town=row["town"],
            county=MAINE_COUNTIES.get(row["county_fips"], row["county_fips"]),
            acs_year=int(value(row, "acs_year")),
            acs_population=int(value(row, "total_population")),
            median_household_income=float(value(row, "median_household_income")),
            pct_below_poverty=float(value(row, "pct_below_poverty")),
            pct_zero_vehicle_households=float(value(row, "pct_zero_vehicle_households")),
            pct_65_plus=float(value(row, "pct_65_plus")),
            pct_with_disability=float(value(row, "pct_with_disability")),
            pct_under_18=float(value(row, "pct_under_18")),
            pct_cost_burdened_households=float(value(row, "pct_cost_burdened_households")),
            pct_cost_burdened_renter_households=float(value(row, "pct_cost_burdened_renter_households")),
            pct_cost_burdened_owner_households=float(value(row, "pct_cost_burdened_owner_households")),
            pct_vacant_housing_units=float(value(row, "pct_vacant_housing_units")),
            pct_seasonal_housing_units=float(value(row, "pct_seasonal_housing_units")),
            pct_long_commute_workers=float(value(row, "pct_long_commute_workers")),
            pct_work_from_home_workers=float(value(row, "pct_work_from_home_workers")),
            pct_no_internet_or_subscription_households=float(value(row, "pct_no_internet_or_subscription_households")),
        )
        for row in data
    ]
    score_towns(towns)
    return towns


def priority_lane(town: ClimateHousingTown) -> str:
    if town.resilience_investment_priority_score >= 60 and town.housing_need_score >= 60:
        return "resilience-first housing and infrastructure planning"
    if town.infrastructure_efficiency_proxy_score >= 60 and town.housing_need_score >= 50:
        return "infrastructure-efficient affordable housing search"
    if town.social_vulnerability_score >= 60:
        return "equity and recovery-capacity priority"
    if town.pct_seasonal_housing_units >= 30 and town.pct_cost_burdened_households >= 30:
        return "seasonal-market pressure and year-round housing review"
    if town.climate_safe_housing_mvp_score >= 55:
        return "priority for FEMA/MGS/wetlands parcel overlay"
    return "monitor and screen after hazard-layer ingestion"


def key_drivers(town: ClimateHousingTown) -> list[str]:
    drivers = {
        "housing cost burden": clamp(town.pct_cost_burdened_households * 2),
        "renter cost burden": clamp(town.pct_cost_burdened_renter_households * 2),
        "poverty": clamp(town.pct_below_poverty * 4),
        "zero-car households": clamp(town.pct_zero_vehicle_households * 4),
        "older adults": clamp(town.pct_65_plus * 2),
        "disability": clamp(town.pct_with_disability * 3),
        "children/family demand": clamp(town.pct_under_18 * 3),
        "seasonal housing pressure": clamp(town.pct_seasonal_housing_units * 3),
        "long commutes": clamp(town.pct_long_commute_workers * 3),
        "digital access gap": clamp(town.pct_no_internet_or_subscription_households * 3),
    }
    return [name for name, _ in sorted(drivers.items(), key=lambda item: item[1], reverse=True)[:4]]


def score_towns(towns: list[ClimateHousingTown]) -> None:
    populations = [town.acs_population for town in towns]
    incomes = [town.median_household_income for town in towns]
    for town in towns:
        population_score = normalize(town.acs_population, populations)
        income_score = normalize(town.median_household_income, incomes)
        cost_burden_need = clamp(town.pct_cost_burdened_households * 2)
        renter_burden_need = clamp(town.pct_cost_burdened_renter_households * 2)
        poverty_need = clamp(town.pct_below_poverty * 4)
        zero_vehicle_need = clamp(town.pct_zero_vehicle_households * 4)
        age_need = clamp(town.pct_65_plus * 2)
        disability_need = clamp(town.pct_with_disability * 3)
        child_need = clamp(town.pct_under_18 * 3)
        seasonal_pressure = clamp(town.pct_seasonal_housing_units * 3)
        long_commute_need = clamp(town.pct_long_commute_workers * 3)
        digital_gap = clamp(town.pct_no_internet_or_subscription_households * 3)
        commute_efficiency = clamp(100 - long_commute_need)
        digital_capacity = clamp(100 - digital_gap)
        year_round_housing_capacity = clamp(100 - seasonal_pressure)

        town.housing_need_score = round(
            0.30 * cost_burden_need
            + 0.20 * renter_burden_need
            + 0.20 * poverty_need
            + 0.15 * seasonal_pressure
            + 0.10 * zero_vehicle_need
            + 0.05 * population_score,
            2,
        )
        town.social_vulnerability_score = round(
            0.25 * poverty_need
            + 0.20 * age_need
            + 0.20 * disability_need
            + 0.15 * zero_vehicle_need
            + 0.10 * digital_gap
            + 0.10 * cost_burden_need,
            2,
        )
        town.infrastructure_efficiency_proxy_score = round(
            0.35 * population_score
            + 0.22 * commute_efficiency
            + 0.18 * digital_capacity
            + 0.10 * clamp(town.pct_work_from_home_workers * 2)
            + 0.10 * income_score
            + 0.05 * year_round_housing_capacity,
            2,
        )
        town.resilience_investment_priority_score = round(
            0.32 * town.social_vulnerability_score
            + 0.25 * town.housing_need_score
            + 0.18 * long_commute_need
            + 0.15 * digital_gap
            + 0.10 * seasonal_pressure,
            2,
        )
        town.climate_safe_housing_mvp_score = round(
            0.34 * town.housing_need_score
            + 0.28 * town.infrastructure_efficiency_proxy_score
            + 0.18 * town.social_vulnerability_score
            + 0.12 * population_score
            + 0.08 * year_round_housing_capacity,
            2,
        )
        town.mvp_priority_lane = priority_lane(town)
        town.key_drivers = key_drivers(town)


def load_screening_table(cfg: dict[str, Any], towns: list[ClimateHousingTown]) -> None:
    run_sql_file(cfg, "sql/03_climate_housing_schema.sql")
    sql = """
        INSERT INTO climate_housing_town_screening (
            town,
            county,
            acs_population,
            housing_need_score,
            social_vulnerability_score,
            infrastructure_efficiency_proxy_score,
            resilience_investment_priority_score,
            climate_safe_housing_mvp_score,
            mvp_priority_lane,
            hazard_overlay_status,
            key_drivers,
            source_year
        )
        VALUES (
            %(town)s,
            %(county)s,
            %(acs_population)s,
            %(housing_need_score)s,
            %(social_vulnerability_score)s,
            %(infrastructure_efficiency_proxy_score)s,
            %(resilience_investment_priority_score)s,
            %(climate_safe_housing_mvp_score)s,
            %(mvp_priority_lane)s,
            %(hazard_overlay_status)s,
            %(key_drivers)s,
            %(source_year)s
        )
        ON CONFLICT (town, county, source_year) DO UPDATE SET
            acs_population = EXCLUDED.acs_population,
            housing_need_score = EXCLUDED.housing_need_score,
            social_vulnerability_score = EXCLUDED.social_vulnerability_score,
            infrastructure_efficiency_proxy_score = EXCLUDED.infrastructure_efficiency_proxy_score,
            resilience_investment_priority_score = EXCLUDED.resilience_investment_priority_score,
            climate_safe_housing_mvp_score = EXCLUDED.climate_safe_housing_mvp_score,
            mvp_priority_lane = EXCLUDED.mvp_priority_lane,
            hazard_overlay_status = EXCLUDED.hazard_overlay_status,
            key_drivers = EXCLUDED.key_drivers,
            created_at = now();
    """
    prepared = [
        {
            "town": town.town,
            "county": town.county,
            "acs_population": town.acs_population,
            "housing_need_score": town.housing_need_score,
            "social_vulnerability_score": town.social_vulnerability_score,
            "infrastructure_efficiency_proxy_score": town.infrastructure_efficiency_proxy_score,
            "resilience_investment_priority_score": town.resilience_investment_priority_score,
            "climate_safe_housing_mvp_score": town.climate_safe_housing_mvp_score,
            "mvp_priority_lane": town.mvp_priority_lane,
            "hazard_overlay_status": "pending FEMA NFHL, MGS SLR/storm-surge, NWI wetlands, conservation, DEM, roads/bridges/culverts overlay",
            "key_drivers": town.key_drivers,
            "source_year": town.acs_year,
        }
        for town in towns
    ]
    with connect(cfg) as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, prepared)


def focus_town_rows(towns: list[ClimateHousingTown], cfg: dict[str, Any]) -> list[list[Any]]:
    focus = set(cfg.get("acs", {}).get("focus_towns", []))
    return [
        [
            town.town,
            town.county,
            fmt(town.climate_safe_housing_mvp_score),
            fmt(town.housing_need_score),
            fmt(town.resilience_investment_priority_score),
            fmt(town.infrastructure_efficiency_proxy_score),
            town.mvp_priority_lane,
        ]
        for town in sorted((town for town in towns if town.town in focus), key=lambda item: item.town)
    ]


def build_markdown(towns: list[ClimateHousingTown], cfg: dict[str, Any]) -> str:
    growth = sorted(towns, key=lambda item: item.climate_safe_housing_mvp_score, reverse=True)
    resilience = sorted(towns, key=lambda item: item.resilience_investment_priority_score, reverse=True)
    housing = sorted(towns, key=lambda item: item.housing_need_score, reverse=True)
    infrastructure = sorted(towns, key=lambda item: item.infrastructure_efficiency_proxy_score, reverse=True)

    def ranked_rows(ranked: list[ClimateHousingTown], score_attr: str) -> list[list[Any]]:
        return [
            [
                rank,
                town.town,
                town.county,
                fmt(getattr(town, score_attr)),
                fmt(town.acs_population),
                f"{fmt(town.pct_cost_burdened_households)}%",
                f"{fmt(town.pct_seasonal_housing_units)}%",
                f"{fmt(town.pct_long_commute_workers)}%",
                "; ".join(town.key_drivers),
            ]
            for rank, town in enumerate(ranked[:35], start=1)
        ]

    return "\n".join([
        "# Climate-Safe Housing Growth Areas MVP Screening",
        "",
        "## What This Is",
        "",
        "This is the same-day MVP for the Maine climate-safe housing research project. It ranks Maine towns using statewide ACS housing, vulnerability, commute, digital-access, and seasonal-housing indicators already loaded in PostGIS.",
        "",
        "It does **not** yet claim that any parcel is climate-safe. FEMA flood zones, Maine Geological Survey sea-level-rise/storm-surge scenarios, wetlands, conserved land, slope, roads, bridges, culverts, parcels, and zoning still need to be spatially overlaid before parcel-level recommendations are made.",
        "",
        "## What It Answers Today",
        "",
        f"- Maine populated towns/county subdivisions screened: **{len(towns)}**.",
        f"- Highest MVP climate-safe housing search priority: **{growth[0].town}**, {growth[0].county} County.",
        f"- Highest resilience investment priority: **{resilience[0].town}**, {resilience[0].county} County.",
        f"- Highest housing pressure signal: **{housing[0].town}**, {housing[0].county} County.",
        f"- Strongest infrastructure-efficiency proxy: **{infrastructure[0].town}**, {infrastructure[0].county} County.",
        "",
        "## MVP Scoring Logic",
        "",
        markdown_table(
            ["Score", "Inputs", "Purpose"],
            [
                ["Housing need", "cost burden, renter burden, poverty, seasonal housing, zero-car households, population scale", "Find towns where housing production or year-round affordability pressure is high."],
                ["Social vulnerability", "poverty, older adults, disability, zero-car households, digital gap, cost burden", "Find towns where climate disruption and housing instability could hurt people most."],
                ["Infrastructure-efficiency proxy", "population scale, commute efficiency, digital capacity, work-from-home, income, year-round housing capacity", "Identify towns that may support efficient growth before detailed road/utility overlays."],
                ["Resilience investment priority", "social vulnerability, housing need, long commutes, digital gap, seasonal pressure", "Find places where public investment should come before or alongside housing growth."],
                ["MVP climate-safe housing search priority", "housing need, infrastructure proxy, vulnerability, population scale, year-round capacity", "Rank where to run the next parcel-level FEMA/MGS/wetlands/roads overlay first."],
            ],
        ),
        "",
        "## Top MVP Climate-Safe Housing Search Priorities",
        "",
        markdown_table(
            ["Rank", "Town", "County", "Score", "Population", "Cost Burden", "Seasonal Housing", "Long Commute", "Key Drivers"],
            ranked_rows(growth, "climate_safe_housing_mvp_score"),
        ),
        "",
        "## Top Resilience Investment Priorities",
        "",
        markdown_table(
            ["Rank", "Town", "County", "Score", "Population", "Cost Burden", "Seasonal Housing", "Long Commute", "Key Drivers"],
            ranked_rows(resilience, "resilience_investment_priority_score"),
        ),
        "",
        "## Top Housing Pressure Signals",
        "",
        markdown_table(
            ["Rank", "Town", "County", "Score", "Population", "Cost Burden", "Seasonal Housing", "Long Commute", "Key Drivers"],
            ranked_rows(housing, "housing_need_score"),
        ),
        "",
        "## Strongest Infrastructure-Efficiency Proxies",
        "",
        markdown_table(
            ["Rank", "Town", "County", "Score", "Population", "Cost Burden", "Seasonal Housing", "Long Commute", "Key Drivers"],
            ranked_rows(infrastructure, "infrastructure_efficiency_proxy_score"),
        ),
        "",
        "## Focus Towns",
        "",
        markdown_table(
            ["Town", "County", "MVP Score", "Housing Need", "Resilience Priority", "Infrastructure Proxy", "Lane"],
            focus_town_rows(towns, cfg),
        ),
        "",
        "## Next Spatial Layers To Ingest",
        "",
        markdown_table(
            ["Priority", "Layer", "Why It Matters"],
            [
                [1, "FEMA NFHL flood zones", "Turns town screening into real flood-exposure screening."],
                [2, "Maine Geological Survey SLR/storm-surge scenarios", "Identifies coastal land that may be unsuitable under future sea-level and storm scenarios."],
                [3, "USFWS NWI wetlands and Maine conservation lands", "Creates hard environmental exclusions."],
                [4, "USGS 3DEP DEM slope/elevation", "Adds low-lying land, slope, and terrain buildability constraints."],
                [5, "MaineDOT roads, bridges, and culverts", "Adds infrastructure access and vulnerability."],
                [6, "Parcels and zoning for pilot towns", "Converts statewide screening into local site-selection products."],
            ],
        ),
        "",
        "## Source Context",
        "",
        "- U.S. Census Bureau ACS 2024 5-year table-based Summary File, loaded in `acs_town_demographics`.",
        "- The project schema now includes empty PostGIS tables for hazard zones, environmental constraints, infrastructure assets, and candidate units.",
        "- Hazard overlay status for this MVP: pending FEMA NFHL, MGS SLR/storm-surge, NWI wetlands, conservation, DEM, roads/bridges/culverts overlay.",
        "",
    ])


def write_csv(path: Path, towns: list[ClimateHousingTown]) -> None:
    fields = [
        "town",
        "county",
        "acs_year",
        "acs_population",
        "climate_safe_housing_mvp_score",
        "housing_need_score",
        "social_vulnerability_score",
        "infrastructure_efficiency_proxy_score",
        "resilience_investment_priority_score",
        "mvp_priority_lane",
        "key_drivers",
        "pct_cost_burdened_households",
        "pct_cost_burdened_renter_households",
        "pct_below_poverty",
        "pct_zero_vehicle_households",
        "pct_65_plus",
        "pct_with_disability",
        "pct_under_18",
        "pct_seasonal_housing_units",
        "pct_long_commute_workers",
        "pct_no_internet_or_subscription_households",
        "hazard_overlay_status",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for town in sorted(towns, key=lambda item: item.climate_safe_housing_mvp_score, reverse=True):
            writer.writerow({
                "town": town.town,
                "county": town.county,
                "acs_year": town.acs_year,
                "acs_population": town.acs_population,
                "climate_safe_housing_mvp_score": town.climate_safe_housing_mvp_score,
                "housing_need_score": town.housing_need_score,
                "social_vulnerability_score": town.social_vulnerability_score,
                "infrastructure_efficiency_proxy_score": town.infrastructure_efficiency_proxy_score,
                "resilience_investment_priority_score": town.resilience_investment_priority_score,
                "mvp_priority_lane": town.mvp_priority_lane,
                "key_drivers": "; ".join(town.key_drivers),
                "pct_cost_burdened_households": town.pct_cost_burdened_households,
                "pct_cost_burdened_renter_households": town.pct_cost_burdened_renter_households,
                "pct_below_poverty": town.pct_below_poverty,
                "pct_zero_vehicle_households": town.pct_zero_vehicle_households,
                "pct_65_plus": town.pct_65_plus,
                "pct_with_disability": town.pct_with_disability,
                "pct_under_18": town.pct_under_18,
                "pct_seasonal_housing_units": town.pct_seasonal_housing_units,
                "pct_long_commute_workers": town.pct_long_commute_workers,
                "pct_no_internet_or_subscription_households": town.pct_no_internet_or_subscription_households,
                "hazard_overlay_status": "pending FEMA NFHL, MGS SLR/storm-surge, NWI wetlands, conservation, DEM, roads/bridges/culverts overlay",
            })


def write_outputs(config_path: str = "configs/project.toml", pdf: bool = False) -> list[Path]:
    cfg = load_config(config_path)
    ensure_directories(cfg)
    towns = fetch_towns(cfg)
    load_screening_table(cfg, towns)
    reports_dir = resolve_path(cfg, "reports_dir")
    markdown = build_markdown(towns, cfg)
    md_path = reports_dir / "climate_safe_housing_mvp_report.md"
    html_path = reports_dir / "climate_safe_housing_mvp_report.html"
    csv_path = reports_dir / "climate_safe_housing_town_screening.csv"
    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(build_html_document(markdown, "Climate-Safe Housing Growth Areas MVP"), encoding="utf-8")
    write_csv(csv_path, towns)
    outputs = [md_path, html_path, csv_path]
    if pdf:
        outputs.append(export_pdf(html_path))
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the same-day climate-safe housing MVP screening report.")
    parser.add_argument("--config", default="configs/project.toml")
    parser.add_argument("--pdf", action="store_true", help="Export the HTML report to PDF.")
    args = parser.parse_args()
    for path in write_outputs(args.config, pdf=args.pdf):
        print(path)


if __name__ == "__main__":
    main()
