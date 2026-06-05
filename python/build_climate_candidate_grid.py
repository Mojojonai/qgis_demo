from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from build_future_reports import build_html_document, export_pdf
from config import ensure_directories, load_config, resolve_path
from db import connect, run_sql_file


CSV_COLUMNS = [
    "unit_id",
    "town",
    "county",
    "buildable_area_sq_km",
    "excluded_area_sq_km",
    "climate_safe_suitability_score",
    "suitability_tier",
    "housing_need_score",
    "social_vulnerability_score",
    "infrastructure_access_score",
    "flood_exposure_score",
    "environmental_constraint_score",
    "review_notes",
]


def score(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def whole(value: Any) -> str:
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return "0"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        safe = [str(item).replace("\n", " ").replace("|", "/") for item in row]
        lines.append("| " + " | ".join(safe) + " |")
    return "\n".join(lines)


def run_grid_model(cfg: dict[str, Any]) -> None:
    run_sql_file(cfg, "sql/03_climate_housing_schema.sql")
    run_sql_file(cfg, "sql/04_climate_candidate_grid.sql")


def fetch_rows(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    query = """
        SELECT
            unit_id,
            town,
            county,
            buildable_area_sq_m / 1000000.0 AS buildable_area_sq_km,
            excluded_area_sq_m / 1000000.0 AS excluded_area_sq_km,
            climate_safe_suitability_score,
            suitability_tier,
            housing_need_score,
            social_vulnerability_score,
            infrastructure_access_score,
            flood_exposure_score,
            environmental_constraint_score,
            review_notes,
            raw_properties
        FROM climate_housing_candidate_units
        WHERE unit_type = 'statewide_5km_grid'
        ORDER BY climate_safe_suitability_score DESC NULLS LAST, town, county;
    """
    with connect(cfg) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [description.name for description in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def fetch_source_counts(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    query = """
        SELECT 'hazard polygon' AS source_role, source_name, COUNT(*) AS feature_count
        FROM climate_housing_hazard_zones
        GROUP BY source_name
        UNION ALL
        SELECT 'environmental constraint' AS source_role, source_name, COUNT(*) AS feature_count
        FROM climate_housing_environmental_constraints
        GROUP BY source_name
        UNION ALL
        SELECT 'infrastructure/exposed asset' AS source_role, source_name, COUNT(*) AS feature_count
        FROM climate_housing_infrastructure_assets
        GROUP BY source_name
        ORDER BY source_role, source_name;
    """
    with connect(cfg) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [description.name for description in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in CSV_COLUMNS})


def export_geojson(cfg: dict[str, Any], path: Path, max_features: int | None = None) -> int:
    limit_sql = "" if max_features is None else "LIMIT %s"
    query = f"""
        SELECT
            unit_id,
            town,
            county,
            buildable_area_sq_m,
            excluded_area_sq_m,
            flood_exposure_score,
            environmental_constraint_score,
            infrastructure_access_score,
            social_vulnerability_score,
            housing_need_score,
            climate_safe_suitability_score,
            suitability_tier,
            review_notes,
            raw_properties,
            ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, 0.0015)) AS geometry
        FROM climate_housing_candidate_units
        WHERE unit_type = 'statewide_5km_grid'
        ORDER BY climate_safe_suitability_score DESC NULLS LAST
        {limit_sql};
    """
    features: list[dict[str, Any]] = []
    with connect(cfg) as conn:
        with conn.cursor() as cur:
            if max_features is None:
                cur.execute(query)
            else:
                cur.execute(query, (max_features,))
            columns = [description.name for description in cur.description]
            for row in cur.fetchall():
                record = dict(zip(columns, row))
                geometry = json.loads(record.pop("geometry"))
                features.append({"type": "Feature", "properties": record, "geometry": geometry})
    payload = {
        "type": "FeatureCollection",
        "metadata": {
            "title": "Climate-safe housing candidate grid",
            "unit_type": "statewide_5km_grid",
            "model_status": "planning-grade grid screen; parcel/hazard confirmation still required",
            "feature_count": len(features),
            "max_features": max_features,
        },
        "features": features,
    }
    path.write_text(json.dumps(payload, separators=(",", ":"), default=str), encoding="utf-8")
    return len(features)


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tiers: dict[str, int] = {}
    counties: dict[str, dict[str, Any]] = {}
    for row in rows:
        tier = str(row.get("suitability_tier") or "unknown")
        tiers[tier] = tiers.get(tier, 0) + 1
        county = str(row.get("county") or "Unknown")
        item = counties.setdefault(county, {"county": county, "count": 0, "score_sum": 0.0, "strong": 0, "hazard_review": 0})
        item["count"] += 1
        item["score_sum"] += float(row.get("climate_safe_suitability_score") or 0)
        if tier == "strong candidate for parcel screening":
            item["strong"] += 1
        if tier == "avoid or detailed hazard review":
            item["hazard_review"] += 1
    county_rows = []
    for item in counties.values():
        count = max(1, int(item["count"]))
        item["avg_score"] = item["score_sum"] / count
        county_rows.append(item)
    return {
        "tiers": dict(sorted(tiers.items(), key=lambda item: item[1], reverse=True)),
        "counties": sorted(county_rows, key=lambda item: (item["strong"], item["avg_score"]), reverse=True),
    }


def build_report(rows: list[dict[str, Any]], geojson_count: int, source_counts: list[dict[str, Any]]) -> str:
    summary = summarize(rows)
    top_candidates = rows[:20]
    hazard_review = [row for row in rows if row.get("suitability_tier") == "avoid or detailed hazard review"][:20]
    resilience = [row for row in rows if row.get("suitability_tier") == "resilience before growth"][:20]

    def row_table(items: list[dict[str, Any]]) -> str:
        return markdown_table(
            ["Grid Unit", "Town", "County", "Score", "Tier", "Flood", "Env", "Infra", "Housing", "Vulnerability"],
            [
                [
                    row["unit_id"],
                    row["town"],
                    row["county"],
                    score(row["climate_safe_suitability_score"]),
                    row["suitability_tier"],
                    score(row["flood_exposure_score"]),
                    score(row["environmental_constraint_score"]),
                    score(row["infrastructure_access_score"]),
                    score(row["housing_need_score"]),
                    score(row["social_vulnerability_score"]),
                ]
                for row in items
            ],
        )

    tier_rows = [[tier, whole(count)] for tier, count in summary["tiers"].items()]
    county_rows = [
        [item["county"], whole(item["count"]), score(item["avg_score"]), whole(item["strong"]), whole(item["hazard_review"])]
        for item in summary["counties"][:16]
    ]
    source_rows = [
        [item["source_role"], item["source_name"], whole(item["feature_count"])]
        for item in source_counts
    ]
    hazard_count = sum(int(item["feature_count"]) for item in source_counts if item["source_role"] == "hazard polygon")
    environment_count = sum(
        int(item["feature_count"]) for item in source_counts if item["source_role"] == "environmental constraint"
    )
    asset_count = sum(
        int(item["feature_count"]) for item in source_counts if item["source_role"] == "infrastructure/exposed asset"
    )

    return "\n\n".join(
        [
            "# Climate-Safe Housing Candidate Grid Model",
            "## What This Adds",
            "This model converts Maine town screening results into statewide 5 km planning grid units. Each grid cell inherits town-level housing need, social vulnerability, and infrastructure proxy scores, then adds exposure signals from loaded hazard zones, environmental constraints, and nearby climate/infrastructure assets.",
            "The result is a first grid-level suitability screen. It is more spatially explicit than town rankings, but it is not a parcel suitability determination. This build includes bounded FEMA NFHL polygons, the queryable Maine conserved-land service, and climate/infrastructure assets. Complete FEMA and NWI coverage, Maine Geological Survey inundation, DEM/slope, zoning, water/wastewater, and parcels are still required before final build/no-build decisions.",
            "## Model Formula",
            markdown_table(
                ["Component", "Weight", "Meaning"],
                [
                    ["Housing need", "30%", "Prioritizes places where housing pressure is visible."],
                    ["Infrastructure access proxy", "30%", "Rewards locations in towns with stronger service/access indicators and nearby road structures."],
                    ["Low flood exposure", "20%", "Penalizes loaded flood/SLR hazard and exposed-asset signals."],
                    ["Low environmental constraint", "10%", "Penalizes loaded wetland/conservation/environmental constraint intersections."],
                    ["Lower social vulnerability", "10%", "Avoids treating highly vulnerable communities as simple growth targets without safeguards."],
                ],
            ),
            "## Output Snapshot",
            markdown_table(
                ["KPI", "Value"],
                [
                    ["Candidate grid units in PostGIS", whole(len(rows))],
                    ["Grid units exported to GeoJSON", whole(geojson_count)],
                    ["Strong candidate units", whole(summary["tiers"].get("strong candidate for parcel screening", 0))],
                    ["Moderate candidate units", whole(summary["tiers"].get("moderate candidate for parcel screening", 0))],
                    ["Avoid or detailed hazard review units", whole(summary["tiers"].get("avoid or detailed hazard review", 0))],
                    ["Resilience-before-growth units", whole(summary["tiers"].get("resilience before growth", 0))],
                    ["Loaded hazard polygons", whole(hazard_count)],
                    ["Loaded environmental constraints", whole(environment_count)],
                    ["Loaded infrastructure/exposed assets", whole(asset_count)],
                ],
            ),
            "## Loaded Spatial Evidence",
            markdown_table(["Role", "Source", "Features In PostGIS"], source_rows),
            "## Suitability Tier Counts",
            markdown_table(["Tier", "Grid Units"], tier_rows),
            "## Highest Scoring Candidate Grid Units",
            row_table(top_candidates),
            "## Grid Units Requiring Avoidance Or Detailed Hazard Review",
            row_table(hazard_review),
            "## Resilience-Before-Growth Grid Units",
            row_table(resilience),
            "## County Portfolio Summary",
            markdown_table(["County", "Grid Units", "Avg Score", "Strong Candidates", "Hazard Review"], county_rows),
            "## How To Use This Output",
            "- Use strong and moderate candidate grid units to choose where parcel screening should start.",
            "- Use avoid/review units as a warning layer, not as a final legal restriction.",
            "- Use resilience-before-growth units to prioritize infrastructure, anti-displacement, emergency access, and recovery-capacity investment.",
            "- Use the GeoJSON in QGIS or the web app as a planning overlay with the existing town-screening outputs.",
            "## Next Precision Step",
            "Replace the 5 km grid with parcel or 250 m grid cells in pilot towns after full hazard, wetlands, conservation, DEM/slope, zoning, roads, bridges, culverts, water/wastewater, and parcel layers are loaded.",
        ]
    )


def write_outputs(config_path: str = "configs/project.toml", pdf: bool = False, max_geojson_features: int | None = 5000) -> list[Path]:
    cfg = load_config(config_path)
    ensure_directories(cfg)
    reports_dir = resolve_path(cfg, "reports_dir")
    run_grid_model(cfg)
    rows = fetch_rows(cfg)
    source_counts = fetch_source_counts(cfg)

    csv_path = reports_dir / "climate_housing_candidate_grid.csv"
    geojson_path = reports_dir / "climate_housing_candidate_grid.geojson"
    md_path = reports_dir / "climate_housing_candidate_grid_report.md"
    html_path = reports_dir / "climate_housing_candidate_grid_report.html"

    write_csv(rows, csv_path)
    geojson_count = export_geojson(cfg, geojson_path, max_features=max_geojson_features)
    markdown = build_report(rows, geojson_count, source_counts)
    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(build_html_document(markdown, "Climate-Safe Housing Candidate Grid Model"), encoding="utf-8")

    outputs = [csv_path, geojson_path, md_path, html_path]
    if pdf:
        outputs.append(export_pdf(html_path))
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Build climate-safe housing candidate grid units and reports.")
    parser.add_argument("--config", default="configs/project.toml")
    parser.add_argument("--pdf", action="store_true")
    parser.add_argument("--max-geojson-features", type=int, default=5000)
    args = parser.parse_args()
    for path in write_outputs(args.config, pdf=args.pdf, max_geojson_features=args.max_geojson_features):
        print(path)


if __name__ == "__main__":
    main()
