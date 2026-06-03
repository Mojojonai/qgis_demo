from __future__ import annotations

import argparse
import html
import subprocess
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from config import ensure_directories, load_config, resolve_path
from db import connect


def rows(cfg: dict[str, Any], sql: str) -> list[tuple[Any, ...]]:
    with connect(cfg) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()


def scalar(cfg: dict[str, Any], sql: str) -> Any:
    result = rows(cfg, sql)
    return result[0][0] if result else None


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return f"{int(value):,}"
        return f"{value:,.2f}"
    return html.escape(str(value))


def table(headers: Iterable[str], data: Iterable[Iterable[Any]]) -> str:
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = "\n".join(
        "<tr>" + "".join(f"<td>{fmt(value)}</td>" for value in row) + "</tr>"
        for row in data
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def pct(value: Any) -> str:
    return f"{float(value):.2f}%"


def build_html(config_path: str = "configs/project.toml") -> Path:
    cfg = load_config(config_path)
    ensure_directories(cfg)
    reports_dir = resolve_path(cfg, "reports_dir")
    map_png = reports_dir / "transit_accessibility_map.png"

    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    postgis_version = scalar(cfg, "SELECT postgis_full_version();")

    counts = rows(cfg, """
        SELECT 'Transit stops' AS layer, COUNT(*) FROM transit_stops
        UNION ALL SELECT 'Transit routes', COUNT(*) FROM transit_routes
        UNION ALL SELECT 'Sidewalk segments', COUNT(*) FROM sidewalks
        UNION ALL SELECT 'Study-area polygons', COUNT(*) FROM study_area
        UNION ALL SELECT 'Neighborhoods', COUNT(*) FROM neighborhoods
        UNION ALL SELECT 'Schools', COUNT(*) FROM schools
        UNION ALL SELECT 'Hospitals', COUNT(*) FROM hospitals
        ORDER BY layer;
    """)
    coverage = rows(cfg, """
        SELECT
            buffer_m || ' m',
            population_inside,
            population_outside,
            pct_population_inside || '%'
        FROM coverage_summary
        ORDER BY buffer_m;
    """)
    scores = rows(cfg, """
        SELECT
            neighborhood_name,
            population,
            accessibility_score,
            transit_score,
            sidewalk_score,
            school_score,
            hospital_score,
            nearest_stop_distance_m
        FROM accessibility_scores
        ORDER BY accessibility_score DESC;
    """)
    underserved = rows(cfg, """
        SELECT
            underserved_rank,
            neighborhood_name,
            accessibility_score,
            nearest_stop_distance_m,
            score_below_40,
            farther_than_800m
        FROM underserved_areas
        ORDER BY underserved_rank;
    """)
    top = scores[:3]
    bottom = list(reversed(scores[-3:])) if len(scores) >= 3 else scores

    coverage_800 = rows(cfg, """
        SELECT population_inside, population_outside, pct_population_inside
        FROM coverage_summary
        WHERE buffer_m = 800;
    """)
    if coverage_800:
        cov_inside, cov_outside, cov_pct = coverage_800[0]
        coverage_sentence = (
            f"The 800-meter transit stop buffer covers about {cov_inside:,} residents "
            f"({pct(cov_pct)}) across the current neighborhood sample, leaving "
            f"{cov_outside:,} residents outside that access band."
        )
    else:
        coverage_sentence = "Coverage statistics were not available."

    map_src = map_png.name if map_png.exists() else ""
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Transit Accessibility and Spatial Equity Analysis</title>
  <style>
    :root {{
      --ink: #1f2933;
      --muted: #5f6b7a;
      --line: #d7dde5;
      --blue: #0f5fa8;
      --green: #3b7f4f;
      --gold: #b7791f;
      --red: #a83838;
      --paper: #ffffff;
      --soft: #f4f7fb;
    }}
    @page {{ size: Letter; margin: 0.55in; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      background: var(--paper);
      line-height: 1.45;
    }}
    .cover {{
      border-bottom: 3px solid var(--blue);
      padding: 12px 0 18px;
      margin-bottom: 18px;
    }}
    h1 {{
      font-size: 30px;
      margin: 0 0 8px;
      letter-spacing: 0;
    }}
    h2 {{
      font-size: 18px;
      margin: 24px 0 8px;
      color: var(--blue);
      border-bottom: 1px solid var(--line);
      padding-bottom: 4px;
    }}
    h3 {{
      font-size: 14px;
      margin: 16px 0 6px;
      color: var(--ink);
    }}
    p, li {{
      font-size: 11.5px;
    }}
    .subtitle {{
      color: var(--muted);
      font-size: 13px;
      margin: 0;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      margin: 16px 0;
    }}
    .metric {{
      background: var(--soft);
      border: 1px solid var(--line);
      padding: 10px;
    }}
    .metric .label {{
      color: var(--muted);
      font-size: 10px;
      text-transform: uppercase;
    }}
    .metric .value {{
      font-size: 18px;
      font-weight: 700;
      margin-top: 4px;
    }}
    .two-col {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      font-size: 10.5px;
      margin: 8px 0 14px;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 6px 7px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #e9f0f7;
      color: #102a43;
    }}
    tr:nth-child(even) td {{
      background: #fbfcfe;
    }}
    .map {{
      width: 100%;
      border: 1px solid var(--line);
      margin-top: 8px;
    }}
    .callout {{
      border-left: 4px solid var(--gold);
      background: #fff8e8;
      padding: 8px 10px;
      margin: 10px 0;
    }}
    .risk {{
      border-left-color: var(--red);
      background: #fff1f1;
    }}
    .page-break {{
      break-before: page;
    }}
    footer {{
      color: var(--muted);
      font-size: 9px;
      margin-top: 24px;
      border-top: 1px solid var(--line);
      padding-top: 8px;
    }}
  </style>
</head>
<body>
  <section class="cover">
    <h1>Transit Accessibility and Spatial Equity Analysis</h1>
    <p class="subtitle">Greater Portland, Maine | PostgreSQL/PostGIS, Python ETL, Spatial SQL, QGIS Automation</p>
    <p class="subtitle">Generated {html.escape(generated)} from the local PostGIS database on port 5764.</p>
  </section>

  <section class="meta">
    <div class="metric"><div class="label">Transit Stops</div><div class="value">{fmt(dict(counts).get("Transit stops"))}</div></div>
    <div class="metric"><div class="label">Transit Routes</div><div class="value">{fmt(dict(counts).get("Transit routes"))}</div></div>
    <div class="metric"><div class="label">Sidewalk Segments</div><div class="value">{fmt(dict(counts).get("Sidewalk segments"))}</div></div>
    <div class="metric"><div class="label">Neighborhood Units</div><div class="value">{fmt(dict(counts).get("Neighborhoods"))}</div></div>
  </section>

  <h2>Executive Summary</h2>
  <p>
    This project evaluates transit accessibility and spatial equity across a first-run Greater Portland analysis area.
    The pipeline downloads public GPCOG transit, route, sidewalk, and study-area layers, loads them into PostGIS,
    runs spatial SQL, and exports a QGIS map and report-ready findings.
  </p>
  <p>{html.escape(coverage_sentence)}</p>
  <div class="callout risk">
    <p>
      Important interpretation note: neighborhoods, schools, and hospitals are currently synthetic sample records.
      They keep the end-to-end workflow operational while verified public Census and facility datasets are added.
      Treat the workflow, SQL, and cartographic automation as production structure, and treat current neighborhood-level
      scores as demonstration values until those layers are replaced.
    </p>
  </div>

  <div class="two-col">
    <div>
      <h3>Strongest Accessibility Scores</h3>
      {table(["Neighborhood", "Population", "Score", "Transit", "Sidewalk", "School", "Hospital", "Nearest Stop m"], top)}
    </div>
    <div>
      <h3>Lowest Accessibility Scores</h3>
      {table(["Neighborhood", "Population", "Score", "Transit", "Sidewalk", "School", "Hospital", "Nearest Stop m"], bottom)}
    </div>
  </div>

  <h2>Map Output</h2>
  <p>
    The map was generated from PostGIS layers using the QGIS Python API. It includes transit routes, stops, sidewalks,
    schools, hospitals, study-area boundaries, graduated accessibility-score polygons, legend, scale bar, and north arrow.
  </p>
  <img class="map" src="{html.escape(map_src)}" alt="Transit accessibility map">

  <h2 class="page-break">Spatial Analysis Results</h2>
  <h3>Transit Coverage Buffers</h3>
  {table(["Buffer", "Population Inside", "Population Outside", "Percent Covered"], coverage)}

  <h3>Accessibility Scores</h3>
  {table(["Neighborhood", "Population", "Accessibility", "Transit", "Sidewalk", "School", "Hospital", "Nearest Stop m"], scores)}

  <h3>Underserved Area Ranking</h3>
  {table(["Rank", "Neighborhood", "Score", "Nearest Stop m", "Score Below 40", "Farther Than 800 m"], underserved)}

  <h2>Methods</h2>
  <p>
    The database uses geometry columns in EPSG:4326 and transforms geometries to EPSG:26919 for meter-based analysis.
    Transit stop buffers are created with <strong>ST_Buffer</strong> and dissolved with <strong>ST_Union</strong>.
    Population coverage is estimated by intersecting neighborhood polygons with 400-meter and 800-meter buffers.
    Nearest stop and facility distances are calculated from neighborhood centroids with projected
    <strong>ST_Distance</strong> measures and KNN-style ordering.
  </p>
  <p>
    The accessibility score is a weighted index from 0 to 100:
    40 percent transit access, 30 percent sidewalk access, 20 percent school access, and 10 percent hospital access.
    Underserved neighborhoods are flagged when the score is below 40, the nearest stop is more than 800 meters away,
    or the polygon is outside the 800-meter transit buffer.
  </p>

  <h2>Technical Summary</h2>
  {table(["Layer", "Records"], counts)}
  <p><strong>PostGIS version:</strong> {html.escape(str(postgis_version))}</p>
  <p>
    Key SQL artifacts: <code>coverage_buffers</code>, <code>coverage_summary</code>,
    <code>nearest_transit_stop</code>, <code>neighborhood_sidewalk_access</code>,
    <code>accessibility_scores</code>, <code>underserved_areas</code>, and
    <code>neighborhood_accessibility_map</code>.
  </p>

  <footer>
    Transit Accessibility and Spatial Equity Analysis for Greater Portland, Maine. Built with Python, PostgreSQL/PostGIS, spatial SQL, and QGIS automation.
  </footer>
</body>
</html>
"""

    output_path = reports_dir / "transit_accessibility_report.html"
    output_path.write_text(html_text, encoding="utf-8")
    return output_path


def find_browser() -> Path | None:
    candidates = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ]
    return next((path for path in candidates if path.exists()), None)


def export_pdf(html_path: Path) -> Path:
    browser = find_browser()
    if not browser:
        raise RuntimeError("No supported browser found for HTML-to-PDF export.")

    pdf_path = html_path.with_suffix(".pdf")
    if pdf_path.exists():
        pdf_path.unlink()

    command = [
        str(browser),
        "--headless",
        "--disable-gpu",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]
    subprocess.run(command, check=True)
    return pdf_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the final portfolio report from PostGIS analysis results.")
    parser.add_argument("--config", default="configs/project.toml")
    parser.add_argument("--pdf", action="store_true", help="Also export HTML report to PDF using Edge or Chrome.")
    args = parser.parse_args()

    html_path = build_html(args.config)
    print(html_path)
    if args.pdf:
        print(export_pdf(html_path))


if __name__ == "__main__":
    main()
