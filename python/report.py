from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from config import ensure_directories, load_config, resolve_path
from db import connect


def fetch_rows(cfg: dict[str, Any], sql: str) -> list[tuple[Any, ...]]:
    with connect(cfg) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return f"{int(value):,}"
        return f"{value:,.2f}"
    return str(value)


def write_report(config_path: str = "configs/project.toml") -> Path:
    cfg = load_config(config_path)
    ensure_directories(cfg)
    reports_dir = resolve_path(cfg, "reports_dir")

    regional = fetch_rows(cfg, """
        WITH town_stats AS (
            SELECT
                COUNT(*) AS town_count,
                SUM(analysis_units) AS analysis_unit_count,
                SUM(total_population) AS total_population,
                ROUND((SUM(weighted_accessibility_score * total_population)::numeric / NULLIF(SUM(total_population), 0)), 2) AS population_weighted_score,
                SUM(underserved_units) AS underserved_units
            FROM town_accessibility_kpis
        ),
        coverage_400 AS (
            SELECT population_inside, pct_population_inside
            FROM coverage_summary
            WHERE buffer_m = 400
        ),
        coverage_800 AS (
            SELECT total_population, population_inside, pct_population_inside
            FROM coverage_summary
            WHERE buffer_m = 800
        )
        SELECT
            ts.town_count,
            ts.analysis_unit_count,
            c800.total_population,
            c400.population_inside AS population_400m,
            c400.pct_population_inside AS pct_pop_400m,
            c800.population_inside AS population_800m,
            c800.pct_population_inside AS pct_pop_800m,
            ts.population_weighted_score,
            ts.underserved_units
        FROM town_stats ts
        CROSS JOIN coverage_400 c400
        CROSS JOIN coverage_800 c800
    """)[0]
    towns = fetch_rows(cfg, """
        SELECT
            town_rank,
            town,
            analysis_units,
            total_population,
            pct_pop_400m,
            pct_pop_800m,
            weighted_accessibility_score,
            avg_nearest_stop_m,
            max_nearest_stop_m,
            underserved_units
        FROM town_accessibility_kpis
        ORDER BY town_rank
    """)
    units = fetch_rows(cfg, """
        SELECT
            town,
            analysis_unit,
            population,
            pct_pop_400m,
            pct_pop_800m,
            nearest_stop_distance_m,
            within_800m,
            accessibility_score,
            lowest_scoring_dimension,
            access_category,
            is_underserved
        FROM analysis_unit_accessibility_kpis
        ORDER BY town, analysis_unit
    """)
    mobility_towns = fetch_rows(cfg, """
        SELECT
            mobility_need_town_rank,
            town,
            acs_town_population,
            weighted_mobility_need_index,
            weighted_accessibility_score,
            pct_zero_vehicle_households,
            pct_below_poverty,
            pct_65_plus,
            pct_with_disability,
            high_need_units,
            dominant_need_driver
        FROM town_mobility_need_index
        ORDER BY mobility_need_town_rank
    """)
    mobility_units = fetch_rows(cfg, """
        SELECT
            mobility_need_rank,
            town,
            analysis_unit,
            mobility_need_index,
            priority_tier,
            primary_need_driver,
            accessibility_gap_score
        FROM mobility_need_index
        ORDER BY mobility_need_rank
    """)
    coverage = fetch_rows(cfg, """
        SELECT buffer_m, population_inside, population_outside, pct_population_inside
        FROM coverage_summary
        ORDER BY buffer_m
    """)
    underserved = fetch_rows(cfg, """
        SELECT underserved_rank, neighborhood_name, accessibility_score, farther_than_800m
        FROM underserved_areas
        ORDER BY underserved_rank
        LIMIT 10
    """)

    lines = [
        "# Executive Summary",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Regional KPI Snapshot",
        "",
    ]
    (
        town_count,
        analysis_unit_count,
        total_population,
        population_400m,
        pct_pop_400m,
        population_800m,
        pct_pop_800m,
        population_weighted_score,
        underserved_units,
    ) = regional
    lines.extend([
        f"- Towns analyzed: {fmt(town_count)}",
        f"- Analysis units: {fmt(analysis_unit_count)}",
        f"- Total population represented: {fmt(total_population)}",
        f"- Population inside 400 m transit access band: {fmt(population_400m)} ({fmt(pct_pop_400m)}%)",
        f"- Population inside 800 m transit access band: {fmt(population_800m)} ({fmt(pct_pop_800m)}%)",
        f"- Population-weighted accessibility score: {fmt(population_weighted_score)}",
        f"- Underserved analysis units: {fmt(underserved_units)}",
    ])
    lines.extend(["", "## All-Town KPI Dashboard", ""])
    lines.extend(
        "- "
        f"{rank}. {town}: units {fmt(units_count)}, population {fmt(population)}, "
        f"400 m coverage {fmt(pct_400)}%, 800 m coverage {fmt(pct_800)}%, "
        f"weighted score {fmt(score)}, avg nearest stop {fmt(avg_stop)} m, "
        f"max nearest stop {fmt(max_stop)} m, underserved units {fmt(underserved_count)}"
        for rank, town, units_count, population, pct_400, pct_800, score, avg_stop, max_stop, underserved_count in towns
    )
    lines.extend(["", "## All Analysis Unit KPI Detail", ""])
    lines.extend(
        "- "
        f"{town} / {unit}: population {fmt(population)}, 400 m coverage {fmt(pct_400)}%, "
        f"800 m coverage {fmt(pct_800)}%, nearest stop {fmt(distance_m)} m, "
        f"within 800 m: {fmt(within_800m)}, score {fmt(score)}, "
        f"limiting dimension {limiting_dimension}, category {category}, underserved: {fmt(is_underserved)}"
        for town, unit, population, pct_400, pct_800, distance_m, within_800m, score, limiting_dimension, category, is_underserved in units
    )
    lines.extend(["", "## Mobility Need Index", ""])
    lines.append(
        "The Mobility Need Index combines the accessibility gap with official ACS 5-year indicators: "
        "zero-vehicle households, poverty, residents age 65 and older, and disability."
    )
    lines.extend(["", "### Town Ranking", ""])
    lines.extend(
        "- "
        f"{rank}. {town}: need index {fmt(need_index)}, access score {fmt(access_score)}, "
        f"ACS population {fmt(acs_population)}, zero-car households {fmt(zero_car)}%, "
        f"poverty {fmt(poverty)}%, age 65+ {fmt(age_65)}%, disability {fmt(disability)}%, "
        f"high-need units {fmt(high_need_units)}, dominant driver {driver}"
        for rank, town, acs_population, need_index, access_score, zero_car, poverty, age_65, disability, high_need_units, driver in mobility_towns
    )
    lines.extend(["", "### Analysis Unit Ranking", ""])
    lines.extend(
        "- "
        f"{rank}. {town} / {unit}: need index {fmt(need_index)}, tier {tier}, "
        f"primary driver {driver}, accessibility gap {fmt(access_gap)}"
        for rank, town, unit, need_index, tier, driver, access_gap in mobility_units
    )
    lines.extend(["", "## Transit Coverage", ""])
    lines.extend(
        f"- {fmt(buffer_m)} m buffer: {fmt(inside)} people inside, {fmt(outside)} outside ({fmt(pct)}% covered)"
        for buffer_m, inside, outside, pct in coverage
    )
    lines.extend(["", "## Underserved Area Ranking", ""])
    if underserved:
        lines.extend(
            f"- {rank}. {name}: score {fmt(score)}, farther than 800 m from transit: {fmt(farther)}"
            for rank, name, score, farther in underserved
        )
    else:
        lines.append("- No neighborhoods met the current underserved thresholds.")
    lines.extend([
        "",
        "## Interactive Dashboard",
        "",
        "Open `reports/mobility_insecurity_dashboard.html` for the interactive MapLibre GL JS, deck.gl, and Apache ECharts dashboard with town filters, tooltips, KPI cards, charts, and the full all-town table.",
    ])
    lines.extend([
        "",
        "## Notes",
        "",
        "This first-run report combines real GPCOG transit, route, study-area, and sidewalk layers with synthetic fallback records for neighborhoods, schools, and hospitals. Replace synthetic layers with verified public datasets before treating the numbers as authoritative.",
    ])

    path = reports_dir / "executive_summary.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate project reports from PostGIS analysis tables.")
    parser.add_argument("--config", default="configs/project.toml")
    args = parser.parse_args()
    path = write_report(args.config)
    print(path)


if __name__ == "__main__":
    main()
