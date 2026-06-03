from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from config import ensure_directories, load_config, resolve_path
from db import connect


def json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def rows(cfg: dict[str, Any], sql: str) -> list[dict[str, Any]]:
    with connect(cfg) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = [description.name for description in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def feature_collection(cfg: dict[str, Any], sql: str) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    for row in rows(cfg, sql):
        geometry = row.pop("geometry")
        if isinstance(geometry, str):
            geometry = json.loads(geometry)
        features.append({"type": "Feature", "geometry": geometry, "properties": row})
    return {"type": "FeatureCollection", "features": features}


def first_row(cfg: dict[str, Any], sql: str) -> dict[str, Any]:
    result = rows(cfg, sql)
    return result[0] if result else {}


def build_payload(cfg: dict[str, Any]) -> dict[str, Any]:
    regional = first_row(cfg, """
        WITH town_stats AS (
            SELECT
                COUNT(*) AS town_count,
                SUM(analysis_units) AS analysis_unit_count,
                SUM(total_population) AS total_population,
                ROUND((SUM(weighted_accessibility_score * total_population)::numeric / NULLIF(SUM(total_population), 0)), 2) AS population_weighted_score,
                ROUND(AVG(avg_nearest_stop_m)::numeric, 2) AS avg_town_nearest_stop_m,
                SUM(underserved_units) AS underserved_units
            FROM town_accessibility_kpis
        ),
        coverage_400 AS (
            SELECT population_inside, population_outside, pct_population_inside
            FROM coverage_summary
            WHERE buffer_m = 400
        ),
        coverage_800 AS (
            SELECT total_population, population_inside, population_outside, pct_population_inside
            FROM coverage_summary
            WHERE buffer_m = 800
        )
        SELECT
            ts.town_count,
            ts.analysis_unit_count,
            c800.total_population,
            c400.population_inside AS population_400m,
            c400.population_outside AS population_outside_400m,
            c400.pct_population_inside AS pct_pop_400m,
            c800.population_inside AS population_800m,
            c800.population_outside AS population_outside_800m,
            c800.pct_population_inside AS pct_pop_800m,
            ts.population_weighted_score,
            ts.avg_town_nearest_stop_m,
            ts.underserved_units
        FROM town_stats ts
        CROSS JOIN coverage_400 c400
        CROSS JOIN coverage_800 c800;
    """)
    towns = rows(cfg, """
        SELECT
            town_rank,
            town,
            analysis_units,
            total_population,
            population_400m,
            pct_pop_400m,
            population_800m,
            pct_pop_800m,
            weighted_accessibility_score,
            avg_accessibility_score,
            min_accessibility_score,
            max_accessibility_score,
            avg_nearest_stop_m,
            max_nearest_stop_m,
            avg_transit_score,
            avg_sidewalk_score,
            avg_school_score,
            avg_hospital_score,
            sidewalk_km,
            sidewalk_m_per_1000_residents,
            schools_inside,
            hospitals_inside,
            units_within_800m,
            units_farther_than_800m,
            underserved_units,
            synthetic_units
        FROM town_accessibility_kpis
        ORDER BY town_rank;
    """)
    units = rows(cfg, """
        SELECT
            accessibility_rank,
            town,
            analysis_unit,
            population,
            median_income,
            population_400m,
            pct_pop_400m,
            population_800m,
            pct_pop_800m,
            nearest_stop_name,
            nearest_route_name,
            nearest_stop_distance_m,
            within_800m,
            accessibility_score,
            transit_score,
            sidewalk_score,
            school_score,
            hospital_score,
            sidewalk_km,
            sidewalk_m_per_1000_residents,
            schools_inside,
            hospitals_inside,
            nearest_school_name,
            nearest_school_distance_m,
            nearest_hospital_name,
            nearest_hospital_distance_m,
            lowest_scoring_dimension,
            access_category,
            is_underserved,
            is_synthetic
        FROM analysis_unit_accessibility_kpis
        ORDER BY town, analysis_unit;
    """)
    units_geojson = feature_collection(cfg, """
        SELECT
            k.accessibility_rank,
            k.town,
            k.analysis_unit,
            k.population,
            k.pct_pop_400m,
            k.pct_pop_800m,
            k.nearest_stop_distance_m,
            k.accessibility_score,
            k.transit_score,
            k.sidewalk_score,
            k.school_score,
            k.hospital_score,
            k.lowest_scoring_dimension,
            k.access_category,
            k.is_underserved,
            ST_AsGeoJSON(n.geom, 6)::json AS geometry
        FROM analysis_unit_accessibility_kpis k
        JOIN neighborhoods n
            ON n.id = k.neighborhood_id
        ORDER BY k.town, k.analysis_unit;
    """)
    stops_geojson = feature_collection(cfg, """
        SELECT
            stop_name,
            route_name,
            is_hub,
            is_on_demand,
            is_wheelchair_accessible,
            ST_AsGeoJSON(geom, 6)::json AS geometry
        FROM transit_stops;
    """)
    routes_geojson = feature_collection(cfg, """
        SELECT
            route_name,
            agency,
            ST_AsGeoJSON(geom, 6)::json AS geometry
        FROM transit_routes;
    """)
    facilities_geojson = feature_collection(cfg, """
        SELECT
            name,
            'School' AS facility_type,
            ST_AsGeoJSON(geom, 6)::json AS geometry
        FROM schools
        UNION ALL
        SELECT
            name,
            'Hospital' AS facility_type,
            ST_AsGeoJSON(geom, 6)::json AS geometry
        FROM hospitals;
    """)
    extent = first_row(cfg, """
        WITH bounds AS (
            SELECT ST_Extent(geom) AS box
            FROM neighborhoods
        )
        SELECT
            ST_XMin(box) AS min_x,
            ST_YMin(box) AS min_y,
            ST_XMax(box) AS max_x,
            ST_YMax(box) AS max_y
        FROM bounds;
    """)
    bounds = [
        [extent.get("min_x", -70.5), extent.get("min_y", 43.56)],
        [extent.get("max_x", -70.2), extent.get("max_y", 43.75)],
    ]
    center = [
        (float(bounds[0][0]) + float(bounds[1][0])) / 2,
        (float(bounds[0][1]) + float(bounds[1][1])) / 2,
    ]
    return {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "regional": regional,
        "towns": towns,
        "units": units,
        "unitsGeojson": units_geojson,
        "stopsGeojson": stops_geojson,
        "routesGeojson": routes_geojson,
        "facilitiesGeojson": facilities_geojson,
        "bounds": bounds,
        "center": center,
    }


def safe_json(data: dict[str, Any]) -> str:
    return json.dumps(data, default=json_default, separators=(",", ":")).replace("</", "<\\/")


def build_html(payload: dict[str, Any]) -> str:
    data_json = safe_json(payload)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Maine Mobility Insecurity Dashboard</title>
  <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@5.7.3/dist/maplibre-gl.css">
  <script src="https://unpkg.com/maplibre-gl@5.7.3/dist/maplibre-gl.js"></script>
  <script src="https://unpkg.com/deck.gl@9.1.12/dist.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
  <style>
    :root {{
      --ink: #1e252c;
      --muted: #5c6875;
      --line: #d7dde5;
      --paper: #ffffff;
      --soft: #f3f6f9;
      --blue: #135c88;
      --green: #25714f;
      --gold: #b27718;
      --red: #a33232;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: #eef2f6;
      font-family: Arial, Helvetica, sans-serif;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 20px;
      align-items: flex-end;
      padding: 18px 22px 14px;
      background: var(--paper);
      border-bottom: 1px solid var(--line);
    }}
    h1 {{
      margin: 0 0 5px;
      font-size: 24px;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 10px;
      font-size: 15px;
      color: var(--blue);
    }}
    h3 {{
      margin: 0 0 7px;
      font-size: 13px;
    }}
    p {{
      margin: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }}
    button, select, label {{
      font: inherit;
    }}
    .shell {{
      display: grid;
      grid-template-columns: minmax(560px, 1.45fr) minmax(380px, 1fr);
      gap: 12px;
      padding: 12px;
    }}
    .panel {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}
    .map-panel {{
      position: relative;
      height: 620px;
    }}
    #map {{
      width: 100%;
      height: 100%;
    }}
    .legend {{
      position: absolute;
      left: 12px;
      bottom: 26px;
      width: 214px;
      background: rgba(255, 255, 255, 0.94);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      box-shadow: 0 10px 24px rgba(31, 41, 55, 0.16);
      font-size: 11px;
      z-index: 5;
    }}
    .legend-row {{
      display: grid;
      grid-template-columns: 18px 1fr;
      gap: 8px;
      align-items: center;
      margin-top: 6px;
    }}
    .swatch {{
      width: 16px;
      height: 16px;
      border-radius: 3px;
      border: 1px solid rgba(0, 0, 0, 0.15);
    }}
    .side {{
      display: grid;
      gap: 12px;
    }}
    .section {{
      padding: 14px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
    }}
    .card {{
      background: var(--soft);
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 10px;
      min-height: 70px;
    }}
    .card .label {{
      color: var(--muted);
      font-size: 10px;
      text-transform: uppercase;
    }}
    .card .value {{
      margin-top: 5px;
      font-weight: 700;
      font-size: 19px;
    }}
    .filters {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      align-items: end;
    }}
    select {{
      width: 100%;
      padding: 8px 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
    }}
    .toggles {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 7px;
      margin-top: 10px;
    }}
    .toggles label {{
      display: flex;
      gap: 7px;
      align-items: center;
      color: var(--muted);
      font-size: 12px;
    }}
    .insights {{
      display: grid;
      gap: 8px;
    }}
    .insight {{
      border-left: 4px solid var(--blue);
      background: #f3f8fb;
      padding: 9px 10px;
      font-size: 12px;
      line-height: 1.4;
    }}
    .insight.warning {{
      border-left-color: var(--gold);
      background: #fff8e8;
    }}
    .insight.risk {{
      border-left-color: var(--red);
      background: #fff1f1;
    }}
    .charts {{
      grid-column: 1 / -1;
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
    }}
    .chart {{
      height: 260px;
      padding: 10px;
    }}
    .table-panel {{
      grid-column: 1 / -1;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }}
    th, td {{
      border-top: 1px solid var(--line);
      padding: 8px 9px;
      text-align: left;
      white-space: nowrap;
    }}
    th {{
      background: #edf3f8;
      color: #1b374e;
      position: sticky;
      top: 0;
    }}
    tbody tr {{
      cursor: pointer;
    }}
    tbody tr:hover td {{
      background: #f7fafc;
    }}
    .detail-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 7px;
      font-size: 12px;
    }}
    .detail-grid div {{
      border-top: 1px solid var(--line);
      padding-top: 7px;
    }}
    .detail-grid strong {{
      display: block;
      color: var(--muted);
      font-size: 10px;
      text-transform: uppercase;
      margin-bottom: 3px;
    }}
    .maplibregl-popup-content {{
      font: 12px Arial, Helvetica, sans-serif;
      color: var(--ink);
    }}
    @media (max-width: 1100px) {{
      .shell, .charts {{
        grid-template-columns: 1fr;
      }}
      .map-panel {{
        height: 520px;
      }}
    }}
    @media (max-width: 720px) {{
      header {{
        display: block;
      }}
      .shell {{
        padding: 8px;
      }}
      .cards, .filters, .toggles, .detail-grid {{
        grid-template-columns: 1fr;
      }}
      th, td {{
        white-space: normal;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Maine Mobility Insecurity Dashboard</h1>
      <p>Greater Portland prototype using PostGIS KPIs, MapLibre GL JS, deck.gl, and Apache ECharts.</p>
    </div>
    <p>Generated <span id="generated"></span></p>
  </header>

  <main class="shell">
    <section class="panel map-panel">
      <div id="map"></div>
      <div class="legend">
        <h3>Accessibility Score</h3>
        <div class="legend-row"><span class="swatch" style="background:#2d9a57"></span><span>80 to 100 high access</span></div>
        <div class="legend-row"><span class="swatch" style="background:#79b75b"></span><span>60 to 79 moderate-high</span></div>
        <div class="legend-row"><span class="swatch" style="background:#e2b348"></span><span>40 to 59 moderate</span></div>
        <div class="legend-row"><span class="swatch" style="background:#c84b3e"></span><span>Below 40 mobility need</span></div>
      </div>
    </section>

    <aside class="side">
      <section class="panel section">
        <h2>Regional Snapshot</h2>
        <div class="cards" id="cards"></div>
      </section>

      <section class="panel section">
        <h2>Explore</h2>
        <div class="filters">
          <label>Town
            <select id="townSelect"></select>
          </label>
          <label>Analysis Unit
            <select id="unitSelect"></select>
          </label>
        </div>
        <div class="toggles">
          <label><input type="checkbox" id="toggleRoutes" checked> Transit routes</label>
          <label><input type="checkbox" id="toggleStops" checked> Transit stops</label>
          <label><input type="checkbox" id="toggleFacilities" checked> Facilities</label>
          <label><input type="checkbox" id="toggleUnderserved" checked> Underserved emphasis</label>
        </div>
      </section>

      <section class="panel section">
        <h2>Selected Place</h2>
        <div id="detail" class="detail-grid"></div>
      </section>

      <section class="panel section">
        <h2>Planning Insights</h2>
        <div id="insights" class="insights"></div>
      </section>
    </aside>

    <section class="panel chart"><div id="scoreChart" style="height:100%"></div></section>
    <section class="panel chart"><div id="coverageChart" style="height:100%"></div></section>
    <section class="panel chart"><div id="componentChart" style="height:100%"></div></section>
    <section class="panel chart"><div id="scatterChart" style="height:100%"></div></section>

    <section class="panel table-panel section">
      <h2>All-Town KPI Table</h2>
      <div style="overflow:auto">
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Town</th>
              <th>Population</th>
              <th>800 m Coverage</th>
              <th>Weighted Score</th>
              <th>Avg Stop m</th>
              <th>Max Stop m</th>
              <th>Underserved Units</th>
              <th>Sidewalk km</th>
            </tr>
          </thead>
          <tbody id="townTable"></tbody>
        </table>
      </div>
    </section>
  </main>

  <script type="application/json" id="dashboard-data">{data_json}</script>
  <script>
    const payload = JSON.parse(document.getElementById('dashboard-data').textContent);
    const fmt = new Intl.NumberFormat('en-US', {{ maximumFractionDigits: 2 }});
    const pct = value => `${{fmt.format(Number(value || 0))}}%`;
    const num = value => fmt.format(Number(value || 0));
    const html = value => String(value ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
    let selectedTown = 'All towns';
    let selectedUnit = 'All units';
    let overlay;
    let popup;

    document.getElementById('generated').textContent = payload.generated;

    function scoreColor(score, alpha = 205) {{
      const s = Number(score || 0);
      if (s >= 80) return [45, 154, 87, alpha];
      if (s >= 60) return [121, 183, 91, alpha];
      if (s >= 40) return [226, 179, 72, alpha];
      return [200, 75, 62, alpha];
    }}

    function filteredUnits() {{
      return payload.units.filter(unit => {{
        const townOk = selectedTown === 'All towns' || unit.town === selectedTown;
        const unitOk = selectedUnit === 'All units' || unit.analysis_unit === selectedUnit;
        return townOk && unitOk;
      }});
    }}

    function filteredUnitFeatures() {{
      const names = new Set(filteredUnits().map(unit => unit.analysis_unit));
      return {{
        type: 'FeatureCollection',
        features: payload.unitsGeojson.features.filter(feature => names.has(feature.properties.analysis_unit))
      }};
    }}

    function renderCards() {{
      const r = payload.regional;
      const cards = [
        ['Towns', r.town_count],
        ['Population', r.total_population],
        ['800 m coverage', pct(r.pct_pop_800m)],
        ['Weighted score', r.population_weighted_score],
        ['Avg stop distance', `${{num(r.avg_town_nearest_stop_m)}} m`],
        ['Underserved units', r.underserved_units]
      ];
      document.getElementById('cards').innerHTML = cards.map(([label, value]) => `
        <div class="card"><div class="label">${{html(label)}}</div><div class="value">${{html(numOrText(value))}}</div></div>
      `).join('');
    }}

    function numOrText(value) {{
      if (typeof value === 'number') return fmt.format(value);
      return value;
    }}

    function renderSelectors() {{
      const townSelect = document.getElementById('townSelect');
      const unitSelect = document.getElementById('unitSelect');
      const towns = ['All towns', ...payload.towns.map(t => t.town)];
      townSelect.innerHTML = towns.map(t => `<option value="${{html(t)}}">${{html(t)}}</option>`).join('');
      townSelect.value = selectedTown;
      const units = ['All units', ...payload.units
        .filter(unit => selectedTown === 'All towns' || unit.town === selectedTown)
        .map(unit => unit.analysis_unit)];
      unitSelect.innerHTML = units.map(t => `<option value="${{html(t)}}">${{html(t)}}</option>`).join('');
      unitSelect.value = units.includes(selectedUnit) ? selectedUnit : 'All units';
      selectedUnit = unitSelect.value;
    }}

    function renderDetails() {{
      const units = filteredUnits();
      const detail = document.getElementById('detail');
      if (!units.length) {{
        detail.innerHTML = '<p>No matching analysis units.</p>';
        return;
      }}
      const unit = selectedUnit === 'All units' ? units[0] : units.find(u => u.analysis_unit === selectedUnit) || units[0];
      detail.innerHTML = [
        ['Town', unit.town],
        ['Analysis unit', unit.analysis_unit],
        ['Population', num(unit.population)],
        ['Score', num(unit.accessibility_score)],
        ['Category', unit.access_category],
        ['Nearest stop', `${{num(unit.nearest_stop_distance_m)}} m`],
        ['800 m coverage', pct(unit.pct_pop_800m)],
        ['Limiting dimension', unit.lowest_scoring_dimension],
        ['Nearest route', unit.nearest_route_name || ''],
        ['Underserved', unit.is_underserved ? 'Yes' : 'No']
      ].map(([label, value]) => `<div><strong>${{html(label)}}</strong>${{html(value)}}</div>`).join('');
    }}

    function renderInsights() {{
      const lowestCoverage = [...payload.towns].sort((a, b) => Number(a.pct_pop_800m) - Number(b.pct_pop_800m))[0];
      const longestStop = [...payload.towns].sort((a, b) => Number(b.avg_nearest_stop_m) - Number(a.avg_nearest_stop_m))[0];
      const weakestScore = [...payload.towns].sort((a, b) => Number(a.weighted_accessibility_score) - Number(b.weighted_accessibility_score))[0];
      const strongestScore = [...payload.towns].sort((a, b) => Number(b.weighted_accessibility_score) - Number(a.weighted_accessibility_score))[0];
      const underserved = payload.towns.filter(t => Number(t.underserved_units) > 0);
      document.getElementById('insights').innerHTML = [
        ['risk', `${{html(weakestScore.town)}} has the lowest weighted accessibility score at ${{num(weakestScore.weighted_accessibility_score)}}.`],
        ['warning', `${{html(lowestCoverage.town)}} has the lowest 800 m coverage at ${{pct(lowestCoverage.pct_pop_800m)}}.`],
        ['warning', `${{html(longestStop.town)}} has the longest average nearest-stop distance at ${{num(longestStop.avg_nearest_stop_m)}} m.`],
        ['', `${{html(strongestScore.town)}} currently leads the prototype with a weighted score of ${{num(strongestScore.weighted_accessibility_score)}}.`],
        ['', `${{underserved.length}} town(s) include at least one underserved analysis unit under the current thresholds.`]
      ].map(([kind, text]) => `<div class="insight ${{kind}}">${{text}}</div>`).join('');
    }}

    function renderTable() {{
      document.getElementById('townTable').innerHTML = payload.towns.map(t => `
        <tr data-town="${{html(t.town)}}">
          <td>${{num(t.town_rank)}}</td>
          <td>${{html(t.town)}}</td>
          <td>${{num(t.total_population)}}</td>
          <td>${{pct(t.pct_pop_800m)}}</td>
          <td>${{num(t.weighted_accessibility_score)}}</td>
          <td>${{num(t.avg_nearest_stop_m)}}</td>
          <td>${{num(t.max_nearest_stop_m)}}</td>
          <td>${{num(t.underserved_units)}}</td>
          <td>${{num(t.sidewalk_km)}}</td>
        </tr>
      `).join('');
      document.querySelectorAll('#townTable tr').forEach(row => {{
        row.addEventListener('click', () => {{
          selectedTown = row.dataset.town;
          selectedUnit = 'All units';
          updateAll();
        }});
      }});
    }}

    const map = new maplibregl.Map({{
      container: 'map',
      style: {{
        version: 8,
        sources: {{
          osm: {{
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png'],
            tileSize: 256,
            attribution: 'OpenStreetMap contributors'
          }}
        }},
        layers: [{{ id: 'osm', type: 'raster', source: 'osm' }}]
      }},
      center: payload.center,
      zoom: 9,
      attributionControl: true
    }});
    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    function layerDataForStops() {{
      if (selectedTown === 'All towns') return payload.stopsGeojson.features;
      return payload.stopsGeojson.features;
    }}

    function buildLayers() {{
      const showRoutes = document.getElementById('toggleRoutes').checked;
      const showStops = document.getElementById('toggleStops').checked;
      const showFacilities = document.getElementById('toggleFacilities').checked;
      const emphasizeUnderserved = document.getElementById('toggleUnderserved').checked;
      const unitsData = filteredUnitFeatures();
      const layers = [
        new deck.GeoJsonLayer({{
          id: 'analysis-units',
          data: unitsData,
          pickable: true,
          stroked: true,
          filled: true,
          getFillColor: f => {{
            const p = f.properties;
            const alpha = emphasizeUnderserved && p.is_underserved ? 230 : 175;
            return scoreColor(p.accessibility_score, alpha);
          }},
          getLineColor: f => f.properties.is_underserved ? [145, 32, 32, 255] : [35, 48, 61, 170],
          getLineWidth: f => f.properties.is_underserved ? 4 : 2,
          lineWidthMinPixels: 1,
          onClick: info => {{
            if (info.object?.properties?.analysis_unit) {{
              selectedTown = info.object.properties.town;
              selectedUnit = info.object.properties.analysis_unit;
              updateAll(false);
            }}
          }}
        }})
      ];
      if (showRoutes) {{
        layers.unshift(new deck.GeoJsonLayer({{
          id: 'routes',
          data: payload.routesGeojson,
          stroked: true,
          filled: false,
          getLineColor: [19, 92, 136, 145],
          getLineWidth: 2,
          lineWidthMinPixels: 1
        }}));
      }}
      if (showStops) {{
        layers.push(new deck.ScatterplotLayer({{
          id: 'stops',
          data: layerDataForStops(),
          pickable: true,
          getPosition: f => f.geometry.coordinates,
          getRadius: 70,
          radiusMinPixels: 3,
          radiusMaxPixels: 9,
          getFillColor: [31, 41, 55, 185],
          getLineColor: [255, 255, 255, 220],
          stroked: true,
          lineWidthMinPixels: 1
        }}));
      }}
      if (showFacilities) {{
        layers.push(new deck.ScatterplotLayer({{
          id: 'facilities',
          data: payload.facilitiesGeojson.features,
          pickable: true,
          getPosition: f => f.geometry.coordinates,
          getRadius: 120,
          radiusMinPixels: 5,
          radiusMaxPixels: 13,
          getFillColor: f => f.properties.facility_type === 'Hospital' ? [163, 50, 50, 215] : [37, 113, 79, 215],
          getLineColor: [255, 255, 255, 230],
          stroked: true,
          lineWidthMinPixels: 1
        }}));
      }}
      return layers;
    }}

    function tooltipFor(object) {{
      if (!object) return null;
      const p = object.properties || object;
      if (p.analysis_unit) {{
        return {{
          html: `<strong>${{html(p.analysis_unit)}}</strong><br>${{html(p.town)}}<br>Score: ${{num(p.accessibility_score)}}<br>800 m coverage: ${{pct(p.pct_pop_800m)}}<br>Nearest stop: ${{num(p.nearest_stop_distance_m)}} m`
        }};
      }}
      if (p.stop_name) return {{ html: `<strong>${{html(p.stop_name)}}</strong><br>${{html(p.route_name || '')}}` }};
      if (p.name) return {{ html: `<strong>${{html(p.name)}}</strong><br>${{html(p.facility_type || '')}}` }};
      return null;
    }}

    function updateLayers() {{
      if (!overlay) return;
      overlay.setProps({{ layers: buildLayers(), getTooltip: info => tooltipFor(info.object) }});
    }}

    map.on('load', () => {{
      overlay = new deck.MapboxOverlay({{
        interleaved: false,
        layers: buildLayers(),
        getTooltip: info => tooltipFor(info.object)
      }});
      map.addControl(overlay);
      const b = payload.bounds;
      map.fitBounds([[b[0][0], b[0][1]], [b[1][0], b[1][1]]], {{ padding: 46, duration: 0 }});
    }});

    function scoreChartOption() {{
      const towns = payload.towns;
      return {{
        title: {{ text: 'Weighted Accessibility Score', left: 8, top: 0, textStyle: {{ fontSize: 13 }} }},
        grid: {{ left: 42, right: 14, bottom: 58, top: 38 }},
        xAxis: {{ type: 'category', data: towns.map(t => t.town), axisLabel: {{ rotate: 35 }} }},
        yAxis: {{ type: 'value', max: 100 }},
        tooltip: {{ trigger: 'axis' }},
        series: [{{
          type: 'bar',
          data: towns.map(t => ({{
            value: t.weighted_accessibility_score,
            itemStyle: {{ color: `rgba(${{scoreColor(t.weighted_accessibility_score, 255).join(',')}})` }}
          }}))
        }}]
      }};
    }}

    function coverageChartOption() {{
      const towns = payload.towns;
      return {{
        title: {{ text: 'Transit Coverage Bands', left: 8, top: 0, textStyle: {{ fontSize: 13 }} }},
        legend: {{ top: 24 }},
        grid: {{ left: 42, right: 14, bottom: 58, top: 58 }},
        xAxis: {{ type: 'category', data: towns.map(t => t.town), axisLabel: {{ rotate: 35 }} }},
        yAxis: {{ type: 'value', max: 100, axisLabel: {{ formatter: '{{value}}%' }} }},
        tooltip: {{ trigger: 'axis' }},
        series: [
          {{ name: '400 m', type: 'bar', data: towns.map(t => t.pct_pop_400m), itemStyle: {{ color: '#b27718' }} }},
          {{ name: '800 m', type: 'bar', data: towns.map(t => t.pct_pop_800m), itemStyle: {{ color: '#135c88' }} }}
        ]
      }};
    }}

    function componentChartOption() {{
      const town = selectedTown === 'All towns' ? payload.towns[0] : payload.towns.find(t => t.town === selectedTown) || payload.towns[0];
      return {{
        title: {{ text: `Component Scores: ${{town.town}}`, left: 8, top: 0, textStyle: {{ fontSize: 13 }} }},
        tooltip: {{}},
        radar: {{
          indicator: [
            {{ name: 'Transit', max: 100 }},
            {{ name: 'Sidewalk', max: 100 }},
            {{ name: 'School', max: 100 }},
            {{ name: 'Hospital', max: 100 }}
          ],
          radius: '62%'
        }},
        series: [{{
          type: 'radar',
          data: [{{
            value: [town.avg_transit_score, town.avg_sidewalk_score, town.avg_school_score, town.avg_hospital_score],
            areaStyle: {{ color: 'rgba(19, 92, 136, 0.18)' }},
            lineStyle: {{ color: '#135c88' }},
            itemStyle: {{ color: '#135c88' }}
          }}]
        }}]
      }};
    }}

    function scatterChartOption() {{
      return {{
        title: {{ text: 'Distance vs Score', left: 8, top: 0, textStyle: {{ fontSize: 13 }} }},
        grid: {{ left: 45, right: 20, bottom: 42, top: 38 }},
        xAxis: {{ name: 'Avg stop m', type: 'value' }},
        yAxis: {{ name: 'Score', type: 'value', max: 100 }},
        tooltip: {{
          formatter: params => `${{html(params.data[3])}}<br>Avg stop: ${{num(params.data[0])}} m<br>Score: ${{num(params.data[1])}}<br>Population: ${{num(params.data[2])}}`
        }},
        series: [{{
          type: 'scatter',
          symbolSize: data => Math.max(8, Math.sqrt(Number(data[2] || 0)) / 12),
          data: payload.towns.map(t => [t.avg_nearest_stop_m, t.weighted_accessibility_score, t.total_population, t.town]),
          itemStyle: {{ color: '#25714f', opacity: 0.78 }}
        }}]
      }};
    }}

    const scoreChart = echarts.init(document.getElementById('scoreChart'));
    const coverageChart = echarts.init(document.getElementById('coverageChart'));
    const componentChart = echarts.init(document.getElementById('componentChart'));
    const scatterChart = echarts.init(document.getElementById('scatterChart'));

    function renderCharts() {{
      scoreChart.setOption(scoreChartOption());
      coverageChart.setOption(coverageChartOption());
      componentChart.setOption(componentChartOption());
      scatterChart.setOption(scatterChartOption());
    }}

    function updateAll(updateMap = true) {{
      renderSelectors();
      renderDetails();
      renderCharts();
      if (updateMap) updateLayers();
    }}

    document.getElementById('townSelect').addEventListener('change', event => {{
      selectedTown = event.target.value;
      selectedUnit = 'All units';
      updateAll();
    }});
    document.getElementById('unitSelect').addEventListener('change', event => {{
      selectedUnit = event.target.value;
      updateAll();
    }});
    ['toggleRoutes', 'toggleStops', 'toggleFacilities', 'toggleUnderserved'].forEach(id => {{
      document.getElementById(id).addEventListener('change', updateLayers);
    }});
    window.addEventListener('resize', () => {{
      scoreChart.resize();
      coverageChart.resize();
      componentChart.resize();
      scatterChart.resize();
    }});

    renderCards();
    renderSelectors();
    renderDetails();
    renderInsights();
    renderTable();
    renderCharts();
  </script>
</body>
</html>
"""


def build_dashboard(config_path: str = "configs/project.toml") -> Path:
    cfg = load_config(config_path)
    ensure_directories(cfg)
    reports_dir = resolve_path(cfg, "reports_dir")
    payload = build_payload(cfg)
    output_path = reports_dir / "mobility_insecurity_dashboard.html"
    output_path.write_text(build_html(payload), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an interactive mobility KPI dashboard from PostGIS.")
    parser.add_argument("--config", default="configs/project.toml")
    args = parser.parse_args()
    print(build_dashboard(args.config))


if __name__ == "__main__":
    main()
