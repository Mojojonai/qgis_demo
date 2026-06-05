from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from config import ensure_directories, load_config, resolve_path
from db import connect


REQUIRED_OUTPUTS = [
    "climate_housing_intelligence_app.html",
    "climate_housing_candidate_grid.csv",
    "climate_housing_candidate_grid.geojson",
    "climate_housing_candidate_grid_report.html",
    "climate_housing_candidate_grid_report.pdf",
    "climate_housing_policy_decision_matrix.csv",
    "climate_housing_policy_decision_matrix.pdf",
    "climate_safe_housing_town_screening.geojson",
]


def fetch_one(cfg: dict[str, Any], sql: str) -> tuple[Any, ...]:
    with connect(cfg) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()


def fetch_all(cfg: dict[str, Any], sql: str) -> list[tuple[Any, ...]]:
    with connect(cfg) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()


def check(label: str, passed: bool, detail: str, severity: str = "FAIL") -> dict[str, str]:
    return {
        "label": label,
        "status": "PASS" if passed else severity,
        "detail": detail,
    }


def build_validation(cfg: dict[str, Any]) -> tuple[list[dict[str, str]], list[tuple[str, str, int]]]:
    checks: list[dict[str, str]] = []
    table_counts = fetch_all(
        cfg,
        """
        SELECT 'Town screening', 'climate_housing_town_screening', COUNT(*) FROM climate_housing_town_screening
        UNION ALL
        SELECT 'Candidate grid', 'climate_housing_candidate_units', COUNT(*) FROM climate_housing_candidate_units
            WHERE unit_type = 'statewide_5km_grid'
        UNION ALL
        SELECT 'Hazard polygons', 'climate_housing_hazard_zones', COUNT(*) FROM climate_housing_hazard_zones
        UNION ALL
        SELECT 'Environmental constraints', 'climate_housing_environmental_constraints', COUNT(*)
            FROM climate_housing_environmental_constraints
        UNION ALL
        SELECT 'Infrastructure/exposed assets', 'climate_housing_infrastructure_assets', COUNT(*)
            FROM climate_housing_infrastructure_assets
        ORDER BY 1;
        """,
    )
    count_map = {table: int(count) for _, table, count in table_counts}
    checks.extend([
        check(
            "Statewide town screen",
            count_map.get("climate_housing_town_screening", 0) >= 400,
            f"{count_map.get('climate_housing_town_screening', 0):,} town records",
        ),
        check(
            "Candidate grid coverage",
            count_map.get("climate_housing_candidate_units", 0) >= 4000,
            f"{count_map.get('climate_housing_candidate_units', 0):,} grid/town units",
        ),
        check(
            "Hazard evidence loaded",
            count_map.get("climate_housing_hazard_zones", 0) > 0,
            f"{count_map.get('climate_housing_hazard_zones', 0):,} polygons",
        ),
        check(
            "Environmental evidence loaded",
            count_map.get("climate_housing_environmental_constraints", 0) > 0,
            f"{count_map.get('climate_housing_environmental_constraints', 0):,} polygons",
        ),
        check(
            "Infrastructure evidence loaded",
            count_map.get("climate_housing_infrastructure_assets", 0) > 0,
            f"{count_map.get('climate_housing_infrastructure_assets', 0):,} assets",
        ),
    ])

    invalid_hazard, invalid_environment, invalid_grid = fetch_one(
        cfg,
        """
        SELECT
            (SELECT COUNT(*) FROM climate_housing_hazard_zones WHERE NOT ST_IsValid(geom)),
            (SELECT COUNT(*) FROM climate_housing_environmental_constraints WHERE NOT ST_IsValid(geom)),
            (SELECT COUNT(*) FROM climate_housing_candidate_units
                WHERE unit_type = 'statewide_5km_grid' AND NOT ST_IsValid(geom));
        """,
    )
    checks.extend([
        check("Hazard geometry validity", int(invalid_hazard) == 0, f"{invalid_hazard} invalid geometries"),
        check("Environmental geometry validity", int(invalid_environment) == 0, f"{invalid_environment} invalid geometries"),
        check("Candidate geometry validity", int(invalid_grid) == 0, f"{invalid_grid} invalid geometries"),
    ])

    minimum, maximum, null_scores, out_of_range, tier_total = fetch_one(
        cfg,
        """
        SELECT
            MIN(climate_safe_suitability_score),
            MAX(climate_safe_suitability_score),
            COUNT(*) FILTER (WHERE climate_safe_suitability_score IS NULL),
            COUNT(*) FILTER (
                WHERE climate_safe_suitability_score < 0 OR climate_safe_suitability_score > 100
            ),
            COUNT(*) FILTER (WHERE suitability_tier IS NOT NULL)
        FROM climate_housing_candidate_units
        WHERE unit_type = 'statewide_5km_grid';
        """,
    )
    candidate_count = count_map.get("climate_housing_candidate_units", 0)
    checks.extend([
        check("Suitability score completeness", int(null_scores) == 0, f"{null_scores} null scores"),
        check(
            "Suitability score range",
            int(out_of_range) == 0,
            f"range {float(minimum or 0):.2f} to {float(maximum or 0):.2f}; {out_of_range} outside 0-100",
        ),
        check("Suitability tier completeness", int(tier_total) == candidate_count, f"{tier_total:,} of {candidate_count:,} classified"),
    ])

    reports_dir = resolve_path(cfg, "reports_dir")
    for name in REQUIRED_OUTPUTS:
        path = reports_dir / name
        exists = path.exists() and path.stat().st_size > 0
        detail = f"{path.stat().st_size:,} bytes" if exists else "missing or empty"
        checks.append(check(f"Output: {name}", exists, detail))

    return checks, [(str(label), str(table), int(count)) for label, table, count in table_counts]


def write_report(cfg: dict[str, Any], checks: list[dict[str, str]], table_counts: list[tuple[str, str, int]]) -> Path:
    path = resolve_path(cfg, "reports_dir") / "climate_housing_validation_report.md"
    pass_count = sum(item["status"] == "PASS" for item in checks)
    fail_count = sum(item["status"] == "FAIL" for item in checks)
    warn_count = sum(item["status"] == "WARN" for item in checks)
    lines = [
        "# Climate Housing Technical Validation Report",
        "",
        "This report is an automated technical quality gate for the current screening release. It does not replace validation against historic flood events, municipal plans, engineering studies, or expert/local review.",
        "",
        "## Validation Summary",
        "",
        f"- Passed checks: **{pass_count}**",
        f"- Failed checks: **{fail_count}**",
        f"- Warning checks: **{warn_count}**",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    lines.extend(f"| {item['label']} | **{item['status']}** | {item['detail']} |" for item in checks)
    lines.extend([
        "",
        "## PostGIS Coverage Snapshot",
        "",
        "| Dataset Role | Table | Records |",
        "| --- | --- | --- |",
    ])
    lines.extend(f"| {label} | `{table}` | {count:,} |" for label, table, count in table_counts)
    lines.extend([
        "",
        "## Remaining External Validation",
        "",
        "- Compare flood-exposure flags with historic flood events, high-water marks, and local hazard-mitigation plans.",
        "- Review high-scoring and avoid/review grid units with municipal planners, MaineHousing, Maine DEP, MaineDOT, and regional planning agencies.",
        "- Load complete NWI wetlands, Maine Geological Survey sea-level-rise/storm-surge, DEM/slope, parcel, zoning, and water/wastewater capacity data before site-level claims.",
        "- Run parcel-scale checks, field verification, and affordability/anti-displacement review before investment or permitting decisions.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate climate-safe housing PostGIS models and deliverables.")
    parser.add_argument("--config", default="configs/project.toml")
    args = parser.parse_args()
    cfg = load_config(args.config)
    ensure_directories(cfg)
    checks, table_counts = build_validation(cfg)
    path = write_report(cfg, checks, table_counts)
    print(path)
    if any(item["status"] == "FAIL" for item in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
