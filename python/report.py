from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from config import ensure_directories, load_config, resolve_path
from db import connect


def fetch_rows(cfg: dict[str, Any], sql: str) -> list[tuple[Any, ...]]:
    with connect(cfg) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()


def write_report(config_path: str = "configs/project.toml") -> Path:
    cfg = load_config(config_path)
    ensure_directories(cfg)
    reports_dir = resolve_path(cfg, "reports_dir")

    top = fetch_rows(cfg, """
        SELECT neighborhood_name, accessibility_score
        FROM accessibility_scores
        ORDER BY accessibility_score DESC
        LIMIT 5
    """)
    bottom = fetch_rows(cfg, """
        SELECT neighborhood_name, accessibility_score, nearest_stop_distance_m
        FROM accessibility_scores
        ORDER BY accessibility_score ASC
        LIMIT 5
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
        "## Most Accessible Neighborhoods",
        "",
    ]
    lines.extend(f"- {name}: {score}" for name, score in top)
    lines.extend(["", "## Least Accessible Neighborhoods", ""])
    lines.extend(f"- {name}: {score} (nearest stop: {distance_m} m)" for name, score, distance_m in bottom)
    lines.extend(["", "## Transit Coverage", ""])
    lines.extend(
        f"- {buffer_m} m buffer: {inside} people inside, {outside} outside ({pct}% covered)"
        for buffer_m, inside, outside, pct in coverage
    )
    lines.extend(["", "## Underserved Area Ranking", ""])
    if underserved:
        lines.extend(
            f"- {rank}. {name}: score {score}, farther than 800 m from transit: {farther}"
            for rank, name, score, farther in underserved
        )
    else:
        lines.append("- No neighborhoods met the current underserved thresholds.")
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
