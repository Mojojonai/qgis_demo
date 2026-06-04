from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from build_future_reports import build_html_document, export_pdf
from config import ensure_directories, load_config, resolve_path


SCORE_COLUMNS = [
    "climate_safe_housing_mvp_score",
    "housing_need_score",
    "social_vulnerability_score",
    "infrastructure_efficiency_proxy_score",
    "resilience_investment_priority_score",
]

PERCENT_COLUMNS = [
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
]

FOCUS_TOWNS = [
    "Portland",
    "South Portland",
    "Westbrook",
    "Brunswick",
    "Kennebunk",
    "Hollis",
    "Cumberland",
    "Falmouth",
    "Scarborough",
    "Gorham",
    "Biddeford",
    "Saco",
    "Bath",
    "Topsham",
    "Freeport",
    "Yarmouth",
    "Windham",
    "Standish",
]


def number(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def whole(value: Any) -> str:
    return f"{int(round(number(value))):,}"


def score(value: Any) -> str:
    return f"{number(value):.2f}"


def pct(value: Any) -> str:
    return f"{number(value):.1f}%"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        safe = [str(item).replace("\n", " ").replace("|", "/") for item in row]
        lines.append("| " + " | ".join(safe) + " |")
    return "\n".join(lines)


def row_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get("town", "")).strip().lower(), str(row.get("county", "")).strip().lower())


def load_geojson_properties(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        merged[row_key(props)] = props
    return merged


def load_screening_rows(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    reports_dir = resolve_path(cfg, "reports_dir")
    csv_path = reports_dir / "climate_safe_housing_town_screening.csv"
    geo_props = load_geojson_properties(reports_dir / "climate_safe_housing_town_screening.geojson")
    rows: list[dict[str, Any]] = []

    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        for raw in csv.DictReader(fh):
            row = dict(raw)
            for column in SCORE_COLUMNS + PERCENT_COLUMNS:
                row[column] = number(row.get(column))
            row["acs_population"] = number(row.get("acs_population"))
            row.update(
                {
                    "climate_asset_sample_count": 0,
                    "bridge_sample_count": 0,
                    "culvert_sample_count": 0,
                    "slr_site_sample_count": 0,
                    "flood_site_sample_count": 0,
                }
            )
            row.update(geo_props.get(row_key(row), {}))
            for column in SCORE_COLUMNS + PERCENT_COLUMNS:
                row[column] = number(row.get(column))
            row["acs_population"] = number(row.get("acs_population"))
            for column in [
                "climate_asset_sample_count",
                "bridge_sample_count",
                "culvert_sample_count",
                "slr_site_sample_count",
                "flood_site_sample_count",
            ]:
                row[column] = number(row.get(column))
            rows.append(row)
    return rows


def action_signals(row: dict[str, Any]) -> list[str]:
    signals: list[str] = []
    if row["climate_safe_housing_mvp_score"] >= 55 and row["infrastructure_efficiency_proxy_score"] >= 54 and row["social_vulnerability_score"] < 60:
        signals.append("near-term housing search")
    if row["resilience_investment_priority_score"] >= 50 and (row["housing_need_score"] >= 50 or row["social_vulnerability_score"] >= 55):
        signals.append("resilience before growth")
    if row["housing_need_score"] >= 60:
        signals.append("high housing need")
    if row["pct_seasonal_housing_units"] >= 25 or "seasonal" in str(row.get("mvp_priority_lane", "")).lower():
        signals.append("seasonal/year-round housing pressure")
    if row["housing_need_score"] >= 50 and row["infrastructure_efficiency_proxy_score"] < 45:
        signals.append("infrastructure capacity gap")
    if row["climate_asset_sample_count"] >= 3:
        signals.append("hazard-overlay first")
    elif row["climate_asset_sample_count"] > 0:
        signals.append("sample asset review")
    if row["pct_no_internet_or_subscription_households"] >= 12:
        signals.append("digital resilience gap")
    if row["pct_long_commute_workers"] >= 18:
        signals.append("workforce commute pressure")
    return signals or ["monitor after hazard-layer ingestion"]


def primary_action(row: dict[str, Any]) -> str:
    if row["climate_asset_sample_count"] >= 5:
        return "Hazard overlay before growth"
    if row["climate_safe_housing_mvp_score"] >= 55 and row["infrastructure_efficiency_proxy_score"] >= 54 and row["social_vulnerability_score"] < 60:
        return "Near-term housing search"
    if row["resilience_investment_priority_score"] >= 50 and (row["housing_need_score"] >= 50 or row["social_vulnerability_score"] >= 55):
        return "Resilience before or alongside growth"
    if row["pct_seasonal_housing_units"] >= 25 or "seasonal" in str(row.get("mvp_priority_lane", "")).lower():
        return "Seasonal market stabilization"
    if row["housing_need_score"] >= 50 and row["infrastructure_efficiency_proxy_score"] < 45:
        return "Infrastructure capacity build-out"
    if row["housing_need_score"] >= 60:
        return "Affordability and parcel screen"
    return "Monitor and screen after hazard layers"


def add_actions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for row in rows:
        signals = action_signals(row)
        row["primary_action"] = primary_action(row)
        row["secondary_signals"] = "; ".join(signals)
        row["decision_note"] = decision_note(row)
    return rows


def decision_note(row: dict[str, Any]) -> str:
    action = row["primary_action"]
    if action == "Hazard overlay before growth":
        return "Sample climate assets are present; run FEMA/MGS/wetlands/conservation/DEM overlays before growth claims."
    if action == "Near-term housing search":
        return "High need and infrastructure proxy make this a strong candidate for parcel-level housing suitability screening."
    if action == "Resilience before or alongside growth":
        return "Housing pressure overlaps vulnerability; pair housing work with recovery capacity and infrastructure resilience."
    if action == "Seasonal market stabilization":
        return "Year-round housing supply and affordability should be separated from seasonal or second-home market pressure."
    if action == "Infrastructure capacity build-out":
        return "Housing need is visible, but transportation/digital/service capacity appears weaker in the MVP screen."
    if action == "Affordability and parcel screen":
        return "Housing need is high; run parcel screening to find buildable, low-risk, infrastructure-efficient locations."
    return "Keep in statewide monitoring queue until complete hazard and environmental layers are ingested."


def top_rows(rows: list[dict[str, Any]], key: str, limit: int = 15, reverse: bool = True) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: number(row.get(key)), reverse=reverse)[:limit]


def action_rows(rows: list[dict[str, Any]], action: str, limit: int = 15) -> list[dict[str, Any]]:
    filtered = [row for row in rows if row["primary_action"] == action]
    return sorted(
        filtered,
        key=lambda row: (
            row["climate_safe_housing_mvp_score"],
            row["housing_need_score"],
            row["resilience_investment_priority_score"],
        ),
        reverse=True,
    )[:limit]


def signal_rows(rows: list[dict[str, Any]], signal: str, limit: int = 15) -> list[dict[str, Any]]:
    filtered = [row for row in rows if signal in row["secondary_signals"]]
    return sorted(
        filtered,
        key=lambda row: (
            row["climate_safe_housing_mvp_score"],
            row["infrastructure_efficiency_proxy_score"],
            row["housing_need_score"],
        ),
        reverse=True,
    )[:limit]


def town_table(rows: list[dict[str, Any]], include_action: bool = True) -> str:
    headers = ["Town", "County", "Population", "MVP", "Housing", "Vulnerability", "Infra", "Resilience", "Assets"]
    if include_action:
        headers.append("Primary action")
    table_rows = []
    for row in rows:
        data = [
            row["town"],
            row["county"],
            whole(row["acs_population"]),
            score(row["climate_safe_housing_mvp_score"]),
            score(row["housing_need_score"]),
            score(row["social_vulnerability_score"]),
            score(row["infrastructure_efficiency_proxy_score"]),
            score(row["resilience_investment_priority_score"]),
            whole(row["climate_asset_sample_count"]),
        ]
        if include_action:
            data.append(row["primary_action"])
        table_rows.append(data)
    return markdown_table(headers, table_rows)


def county_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["county"]].append(row)

    summaries = []
    for county, items in grouped.items():
        top = max(items, key=lambda row: row["climate_safe_housing_mvp_score"])
        actions = Counter(row["primary_action"] for row in items)
        summaries.append(
            {
                "county": county,
                "towns": len(items),
                "population": sum(number(row["acs_population"]) for row in items),
                "avg_mvp": sum(row["climate_safe_housing_mvp_score"] for row in items) / len(items),
                "avg_housing": sum(row["housing_need_score"] for row in items) / len(items),
                "avg_resilience": sum(row["resilience_investment_priority_score"] for row in items) / len(items),
                "near_term": actions["Near-term housing search"],
                "resilience": actions["Resilience before or alongside growth"],
                "hazard": actions["Hazard overlay before growth"],
                "dominant_action": actions.most_common(1)[0][0],
                "top_town": top["town"],
                "top_score": top["climate_safe_housing_mvp_score"],
            }
        )
    return sorted(
        summaries,
        key=lambda row: (row["near_term"], row["resilience"], row["hazard"], row["avg_mvp"]),
        reverse=True,
    )


def county_table(rows: list[dict[str, Any]], limit: int = 16) -> str:
    summaries = county_summary(rows)[:limit]
    return markdown_table(
        ["County", "Towns", "Population", "Avg MVP", "Near-Term", "Resilience", "Hazard First", "Top Town", "Dominant Action"],
        [
            [
                item["county"],
                item["towns"],
                whole(item["population"]),
                score(item["avg_mvp"]),
                item["near_term"],
                item["resilience"],
                item["hazard"],
                f"{item['top_town']} ({score(item['top_score'])})",
                item["dominant_action"],
            ]
            for item in summaries
        ],
    )


def focus_town_table(rows: list[dict[str, Any]]) -> str:
    by_town = {str(row["town"]).lower(): row for row in rows}
    selected = [by_town[name.lower()] for name in FOCUS_TOWNS if name.lower() in by_town]
    return town_table(selected, include_action=True)


def action_matrix_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "town",
        "county",
        "acs_population",
        "primary_action",
        "secondary_signals",
        "decision_note",
        "climate_safe_housing_mvp_score",
        "housing_need_score",
        "social_vulnerability_score",
        "infrastructure_efficiency_proxy_score",
        "resilience_investment_priority_score",
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
        "climate_asset_sample_count",
        "bridge_sample_count",
        "culvert_sample_count",
        "slr_site_sample_count",
        "flood_site_sample_count",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in sorted(rows, key=lambda item: item["climate_safe_housing_mvp_score"], reverse=True):
            writer.writerow({field: row.get(field, "") for field in fields})


def build_markdown(rows: list[dict[str, Any]]) -> str:
    action_counts = Counter(row["primary_action"] for row in rows)
    total_population = sum(number(row["acs_population"]) for row in rows)
    asset_towns = sum(1 for row in rows if row["climate_asset_sample_count"] > 0)
    high_need = sum(1 for row in rows if row["housing_need_score"] >= 60)
    high_vulnerability = sum(1 for row in rows if row["social_vulnerability_score"] >= 60)
    resilience_priority = sum(1 for row in rows if row["resilience_investment_priority_score"] >= 50)

    near_term = signal_rows(rows, "near-term housing search", 20)
    resilience = action_rows(rows, "Resilience before or alongside growth", 20)
    seasonal = action_rows(rows, "Seasonal market stabilization", 20)
    capacity = action_rows(rows, "Infrastructure capacity build-out", 20)
    hazard = action_rows(rows, "Hazard overlay before growth", 20)
    housing_need = top_rows(rows, "housing_need_score", 20)

    return "\n\n".join(
        [
            "# Maine Climate-Safe Housing Policy Decision Matrix",
            "## Purpose",
            "This report converts the town-level climate-safe housing MVP scores into planning actions. It is designed for state, regional, and municipal decision-makers who need to know where to start parcel screening, where resilience investment should come first, and where housing pressure is visible but infrastructure or hazard review must be strengthened.",
            "This is still a planning-grade screen, not a permit map. The next GIS stage must ingest full FEMA NFHL, Maine Geological Survey sea-level-rise and storm-surge, wetlands, conservation land, DEM/slope, parcels, zoning, water/wastewater, road, bridge, and culvert layers before any final build/no-build conclusions.",
            "## Statewide KPI Snapshot",
            markdown_table(
                ["KPI", "Value", "Why It Matters"],
                [
                    ["Populated Maine towns screened", len(rows), "Shows the statewide coverage of the MVP decision matrix."],
                    ["Population represented", whole(total_population), "Estimates how many residents live in screened county subdivisions."],
                    ["High housing-need towns", high_need, "Towns where housing pressure should be investigated first."],
                    ["High social-vulnerability towns", high_vulnerability, "Towns where displacement, recovery capacity, and equity risk deserve attention."],
                    ["Resilience-priority towns", resilience_priority, "Towns where public investment may need to come before or alongside housing growth."],
                    ["Towns with sampled climate assets", asset_towns, "Places touched by the first MaineDOT/DEP sample layers and needing deeper hazard review."],
                    ["Near-term housing search towns", action_counts["Near-term housing search"], "Best first-pass candidates for parcel-level suitability screening."],
                    ["Hazard-overlay-first towns", action_counts["Hazard overlay before growth"], "Places where exposure review should precede growth claims."],
                ],
            ),
            "## Decision Rules",
            markdown_table(
                ["Action Category", "Rule Used In MVP", "Planning Meaning"],
                [
                    ["Near-term housing search", "MVP score >= 55, infrastructure proxy >= 54, vulnerability < 60", "Start parcel-level suitability screening near existing service capacity."],
                    ["Hazard overlay before growth", "Sample climate asset count >= 5", "Do FEMA/MGS/wetlands/conservation/DEM overlays before saying a town has safe growth land."],
                    ["Resilience before or alongside growth", "Resilience score >= 50 plus housing need or vulnerability signal", "Pair housing policy with infrastructure hardening, recovery capacity, and equity investment."],
                    ["Seasonal market stabilization", "Seasonal housing share >= 25% or seasonal lane assignment", "Focus on year-round affordability, workforce housing, and anti-displacement tools."],
                    ["Infrastructure capacity build-out", "Housing need >= 50 and infrastructure proxy < 45", "Housing need exists, but service/transportation/digital capacity may limit growth."],
                    ["Affordability and parcel screen", "Housing need >= 60 outside stronger categories", "Run parcel screening and local policy review for affordable housing production."],
                    ["Monitor and screen after hazard layers", "No strong MVP trigger", "Keep in statewide database and revisit after complete hazard/environment layers."],
                ],
            ),
            "## Near-Term Housing Search Candidates",
            "These towns have high MVP scores, stronger infrastructure-efficiency proxies, and social-vulnerability scores below the highest-risk band. They are not automatically safe to build; they are the best places to run detailed parcel screening first.",
            town_table(near_term),
            "## Resilience Before Or Alongside Growth",
            "These towns show overlap between housing pressure, social vulnerability, recovery-capacity concerns, long commutes, digital gaps, or seasonal pressure. Housing work here should be paired with resilience investment.",
            town_table(resilience),
            "## Hazard-Overlay-First Towns",
            "These towns intersect the first sampled Maine climate/infrastructure assets in the current MVP. This is a flag for deeper hazard overlay, not a final no-build finding.",
            town_table(hazard),
            "## Seasonal Market Stabilization",
            "These towns require special attention to year-round housing, workforce housing, and displacement pressure from seasonal or second-home markets.",
            town_table(seasonal),
            "## Infrastructure Capacity Build-Out",
            "These towns show housing need but weaker infrastructure-efficiency proxy values. The question is not only where to build, but what public capacity must be improved before growth can be equitable and efficient.",
            town_table(capacity),
            "## Highest Housing-Need Signals",
            "This table answers the affordability-pressure side of the research question. These places should be tested against parcel availability, hazard exposure, and infrastructure capacity.",
            town_table(housing_need),
            "## County Portfolio Summary",
            "County summaries help Maine agencies and regional planning organizations decide where technical assistance, hazard-layer completion, and housing planning support should be concentrated.",
            county_table(rows),
            "## Focus Towns Requested For Greater Maine Review",
            "This table keeps the earlier user focus towns visible while the project expands statewide.",
            focus_town_table(rows),
            "## What This Answers For Maine",
            "- Where can Maine start looking for climate-safe housing growth? Start with the near-term housing search towns, then run parcel-level hazard and environmental overlays.",
            "- Which areas should avoid premature development claims? Any hazard-overlay-first town, coastal/riverine town, wetland-rich area, conserved-land area, steep-slope area, or infrastructure-limited town should not be labeled build-ready until full overlays are complete.",
            "- Which towns combine housing need and vulnerability? Use the resilience-before-growth and highest housing-need tables to prioritize resilience funding, anti-displacement support, and recovery-capacity planning.",
            "- Where should governments prioritize investment? Counties and towns with many resilience, hazard-first, and infrastructure-capacity flags should be first in line for technical assistance and capital planning.",
            "- Which places are promising for affordable, infrastructure-efficient housing? Near-term housing search towns are the MVP starting points, especially where parcel overlays later confirm low flood, low wetland, low conservation, moderate slope, and service-access suitability.",
            "## Immediate Next GIS Tasks",
            "1. Replace sample hazard flags with full FEMA NFHL, Maine Geological Survey SLR/storm-surge, NWI wetlands, conserved lands, shoreland, DEM/slope, parcels, zoning, roads, bridges, and culverts.",
            "2. Convert the town matrix into parcel or 250-meter grid suitability scores.",
            "3. Add scenario weights for policy choices: affordable housing, resilience-first, infrastructure-efficient growth, and conservation-first.",
            "4. Validate results against local comprehensive plans, known flood events, and expert review from planners, emergency managers, housing authorities, and conservation staff.",
        ]
    )


def write_outputs(config_path: str = "configs/project.toml", pdf: bool = False) -> list[Path]:
    cfg = load_config(config_path)
    ensure_directories(cfg)
    reports_dir = resolve_path(cfg, "reports_dir")
    rows = add_actions(load_screening_rows(cfg))
    markdown = build_markdown(rows)

    md_path = reports_dir / "climate_housing_policy_decision_matrix.md"
    html_path = reports_dir / "climate_housing_policy_decision_matrix.html"
    csv_path = reports_dir / "climate_housing_policy_decision_matrix.csv"

    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(build_html_document(markdown, "Maine Climate-Safe Housing Policy Decision Matrix"), encoding="utf-8")
    action_matrix_csv(rows, csv_path)

    outputs = [md_path, html_path, csv_path]
    if pdf:
        outputs.append(export_pdf(html_path))
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a policy decision matrix from the climate-safe housing town screen.")
    parser.add_argument("--config", default="configs/project.toml")
    parser.add_argument("--pdf", action="store_true", help="Export the HTML report to PDF.")
    args = parser.parse_args()
    for path in write_outputs(args.config, pdf=args.pdf):
        print(path)


if __name__ == "__main__":
    main()
