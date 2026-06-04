from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from config import ensure_directories, load_config, resolve_path


METRICS = {
    "climate_safe_housing_mvp_score": "MVP Search Priority",
    "housing_need_score": "Housing Need",
    "social_vulnerability_score": "Social Vulnerability",
    "infrastructure_efficiency_proxy_score": "Infrastructure Proxy",
    "resilience_investment_priority_score": "Resilience Priority",
    "climate_asset_sample_count": "Sample Climate Assets",
}

NUMERIC_FIELDS = [
    "acs_population",
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


def number(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def row_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get("town", "")).strip().lower(), str(row.get("county", "")).strip().lower())


def load_policy_matrix(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    if not path.exists():
        return {}
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    with path.open("r", encoding="utf-8", newline="") as fh:
        for raw in csv.DictReader(fh):
            row = dict(raw)
            for field in NUMERIC_FIELDS:
                if field in row:
                    row[field] = number(row.get(field))
            rows[row_key(row)] = row
    return rows


def load_payload(cfg: dict[str, Any]) -> dict[str, Any]:
    reports_dir = resolve_path(cfg, "reports_dir")
    geojson_path = reports_dir / "climate_safe_housing_town_screening.geojson"
    policy_path = reports_dir / "climate_housing_policy_decision_matrix.csv"
    geojson = json.loads(geojson_path.read_text(encoding="utf-8"))
    policy_rows = load_policy_matrix(policy_path)

    for index, feature in enumerate(geojson.get("features", [])):
        props = feature.setdefault("properties", {})
        props.update(policy_rows.get(row_key(props), {}))
        for field in NUMERIC_FIELDS:
            props[field] = number(props.get(field))
        props["_id"] = str(props.get("geoid") or f"{props.get('town', 'town')}-{props.get('county', 'county')}-{index}")
        props.setdefault("primary_action", "Monitor and screen after hazard layers")
        props.setdefault("secondary_signals", "monitor after hazard-layer ingestion")
        props.setdefault("decision_note", "Keep in statewide monitoring queue until complete hazard and environmental layers are ingested.")
        props.setdefault("key_drivers", "")
    geojson.setdefault("metadata", {})
    geojson["metadata"]["app_title"] = "Maine Climate-Safe Housing Intelligence App"
    return geojson


def build_html(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, separators=(",", ":"))
    metrics = json.dumps(METRICS, separators=(",", ":"))
    metric_options = "\n".join(
        f'<option value="{key}">{label}</option>'
        for key, label in METRICS.items()
    )
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Maine Climate-Safe Housing Intelligence App</title>
  <style>
    :root {
      --ink: #17202a;
      --muted: #617080;
      --line: #d8e0e6;
      --panel: #ffffff;
      --page: #edf1f3;
      --soft: #f7f9fa;
      --accent: #1f7a5a;
      --accent-dark: #123f36;
      --blue: #24536b;
      --rust: #8f3b38;
      --gold: #9a6b23;
      --violet: #655d8a;
      --selected: #101820;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      height: 100vh;
      overflow: hidden;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--ink);
      background: var(--page);
    }
    .app {
      display: grid;
      grid-template-columns: 350px minmax(420px, 1fr) 430px;
      height: 100vh;
    }
    aside, .right-panel {
      background: var(--panel);
      overflow: auto;
    }
    .left-panel {
      border-right: 1px solid var(--line);
      padding: 16px;
    }
    .right-panel {
      border-left: 1px solid var(--line);
      padding: 14px;
    }
    .map-panel {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      min-width: 0;
      background: #dbe7e8;
    }
    .map-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      min-height: 48px;
      padding: 10px 14px;
      border-bottom: 1px solid rgba(70,81,92,0.25);
      background: rgba(255,255,255,0.82);
    }
    .map-title {
      font-size: 14px;
      font-weight: 800;
      color: var(--accent-dark);
    }
    .filter-summary {
      font-size: 12px;
      color: var(--muted);
      text-align: right;
    }
    .map-canvas {
      position: relative;
      min-height: 0;
      overflow: hidden;
    }
    #mapSvg {
      width: 100%;
      height: 100%;
      display: block;
      background:
        linear-gradient(0deg, rgba(255,255,255,0.28), rgba(255,255,255,0.28)),
        #dbe7e8;
    }
    #mapSvg path {
      cursor: pointer;
      vector-effect: non-scaling-stroke;
      transition: fill-opacity 120ms ease, stroke-width 120ms ease, opacity 120ms ease;
    }
    #mapSvg path:hover {
      fill-opacity: 0.92;
      stroke-width: 1.7;
    }
    #mapSvg path.selected {
      stroke: var(--selected);
      stroke-width: 2.8;
      fill-opacity: 0.96;
    }
    h1 {
      margin: 0 0 6px;
      font-size: 20px;
      line-height: 1.15;
      letter-spacing: 0;
      color: var(--accent-dark);
    }
    h2 {
      margin: 16px 0 8px;
      font-size: 13px;
      line-height: 1.2;
      text-transform: uppercase;
      letter-spacing: 0;
      color: #2a3a46;
    }
    .subtitle {
      margin: 0 0 14px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }
    .control { margin: 11px 0; }
    label {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      font-size: 11px;
      font-weight: 800;
      color: #3f4b56;
      margin-bottom: 5px;
      text-transform: uppercase;
      letter-spacing: 0;
    }
    select, input[type="search"] {
      width: 100%;
      height: 36px;
      border: 1px solid #cbd5dd;
      border-radius: 4px;
      padding: 0 10px;
      font-size: 13px;
      color: var(--ink);
      background: #fff;
    }
    input[type="range"] {
      width: 100%;
      accent-color: var(--accent);
    }
    button {
      width: 100%;
      height: 36px;
      border: 1px solid #b8c7d0;
      border-radius: 4px;
      background: #fff;
      color: #22313d;
      font-weight: 800;
      cursor: pointer;
    }
    button:hover { background: #f2f6f4; border-color: #7da390; }
    .kpis {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin: 14px 0;
    }
    .kpi {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px;
      background: var(--soft);
      min-height: 70px;
    }
    .kpi .label {
      font-size: 10px;
      color: var(--muted);
      text-transform: uppercase;
      font-weight: 800;
    }
    .kpi .value {
      margin-top: 6px;
      font-size: 20px;
      line-height: 1.08;
      color: var(--accent-dark);
      font-weight: 800;
      overflow-wrap: anywhere;
    }
    .legend {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      padding: 10px;
    }
    .legend-title {
      font-size: 11px;
      font-weight: 800;
      margin-bottom: 8px;
      color: #23313d;
    }
    .legend-row {
      display: grid;
      grid-template-columns: 18px 1fr;
      gap: 8px;
      align-items: center;
      font-size: 11px;
      color: #3f4b56;
      margin: 5px 0;
    }
    .swatch {
      width: 18px;
      height: 12px;
      border: 1px solid rgba(0,0,0,0.18);
    }
    .profile {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--soft);
      padding: 11px;
    }
    .profile-title {
      font-size: 18px;
      line-height: 1.15;
      color: var(--accent-dark);
      font-weight: 800;
      margin-bottom: 6px;
    }
    .pill {
      display: inline-block;
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 11px;
      font-weight: 800;
      color: #fff;
      background: var(--blue);
      margin: 0 0 8px;
    }
    .profile-note {
      font-size: 12px;
      color: #34444f;
      line-height: 1.4;
      margin: 4px 0 8px;
    }
    .detail-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
    }
    .detail-table td {
      border-bottom: 1px solid #e2e8ed;
      padding: 5px 0;
      vertical-align: top;
    }
    .detail-table td:first-child {
      width: 44%;
      color: var(--muted);
    }
    .detail-table td:last-child {
      font-weight: 800;
      padding-left: 10px;
    }
    .chart-box {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      padding: 10px;
      margin: 10px 0;
    }
    .chart-title {
      font-size: 12px;
      text-transform: uppercase;
      font-weight: 800;
      color: #2a3a46;
      margin-bottom: 6px;
    }
    .chart-box svg {
      width: 100%;
      height: auto;
      display: block;
    }
    .town-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
    }
    .town-table th {
      position: sticky;
      top: 0;
      background: #eef3f5;
      z-index: 1;
      text-align: left;
      color: #31424f;
      border-bottom: 1px solid var(--line);
      padding: 6px 5px;
    }
    .town-table td {
      border-bottom: 1px solid #e7edf1;
      padding: 6px 5px;
      vertical-align: top;
    }
    .town-table tr {
      cursor: pointer;
    }
    .town-table tr:hover,
    .town-table tr.active {
      background: #f1f7f4;
    }
    .table-wrap {
      max-height: 330px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
    }
    .tooltip {
      position: fixed;
      display: none;
      pointer-events: none;
      z-index: 5;
      background: rgba(23,32,42,0.94);
      color: #fff;
      border-radius: 4px;
      padding: 7px 8px;
      font-size: 11px;
      line-height: 1.35;
      max-width: 260px;
    }
    .empty-map {
      position: absolute;
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%);
      background: rgba(255,255,255,0.95);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px 14px;
      color: var(--muted);
      font-size: 13px;
      display: none;
    }
    @media (max-width: 1180px) {
      body { overflow: auto; }
      .app {
        grid-template-columns: 340px minmax(0, 1fr);
        grid-template-rows: 65vh auto;
        height: auto;
      }
      .left-panel { grid-column: 1; grid-row: 1 / span 2; }
      .map-panel { grid-column: 2; grid-row: 1; min-height: 65vh; }
      .right-panel { grid-column: 2; grid-row: 2; border-left: 0; border-top: 1px solid var(--line); }
    }
    @media (max-width: 820px) {
      .app { display: block; height: auto; }
      body { height: auto; overflow: auto; }
      .left-panel, .right-panel { border: 0; border-bottom: 1px solid var(--line); }
      .map-panel { min-height: 58vh; }
      .map-canvas { height: 58vh; }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside class="left-panel">
      <h1>Maine Climate-Safe Housing Intelligence App</h1>
      <p class="subtitle">Synchronized town-level screening for housing need, resilience priority, climate asset review, infrastructure proxy, and policy action categories.</p>

      <div class="control">
        <label for="metricSelect">Map Layer</label>
        <select id="metricSelect">__METRIC_OPTIONS__</select>
      </div>
      <div class="control">
        <label for="countySelect">County</label>
        <select id="countySelect"></select>
      </div>
      <div class="control">
        <label for="actionSelect">Policy Action</label>
        <select id="actionSelect"></select>
      </div>
      <div class="control">
        <label for="searchBox">Town Search</label>
        <input id="searchBox" type="search" placeholder="Portland, Brunswick, Kennebunk">
      </div>

      <h2>KPI Filters</h2>
      <div class="control"><label for="mvpRange"><span>Min MVP</span><span id="mvpValue">0</span></label><input id="mvpRange" type="range" min="0" max="100" value="0"></div>
      <div class="control"><label for="housingRange"><span>Min Housing Need</span><span id="housingValue">0</span></label><input id="housingRange" type="range" min="0" max="100" value="0"></div>
      <div class="control"><label for="infraRange"><span>Min Infrastructure</span><span id="infraValue">0</span></label><input id="infraRange" type="range" min="0" max="100" value="0"></div>
      <div class="control"><label for="resilienceRange"><span>Min Resilience</span><span id="resilienceValue">0</span></label><input id="resilienceRange" type="range" min="0" max="100" value="0"></div>
      <div class="control"><label for="vulnerabilityRange"><span>Max Vulnerability</span><span id="vulnerabilityValue">100</span></label><input id="vulnerabilityRange" type="range" min="0" max="100" value="100"></div>
      <button id="resetButton">Reset Filters</button>

      <h2>Filtered KPIs</h2>
      <div class="kpis">
        <div class="kpi"><div class="label">Towns</div><div class="value" id="townCount">0</div></div>
        <div class="kpi"><div class="label">Population</div><div class="value" id="populationCount">0</div></div>
        <div class="kpi"><div class="label">Top Town</div><div class="value" id="topTown">-</div></div>
        <div class="kpi"><div class="label">Avg Layer</div><div class="value" id="avgMetric">0</div></div>
        <div class="kpi"><div class="label">High Housing</div><div class="value" id="highHousing">0</div></div>
        <div class="kpi"><div class="label">Climate Assets</div><div class="value" id="assetTotal">0</div></div>
      </div>

      <h2>Legend</h2>
      <div class="legend" id="legend"></div>
    </aside>

    <main class="map-panel">
      <div class="map-header">
        <div class="map-title" id="mapTitle">Town Screening Map</div>
        <div class="filter-summary" id="filterSummary">Loading</div>
      </div>
      <div class="map-canvas">
        <svg id="mapSvg" viewBox="0 0 1000 720" role="img" aria-label="Maine climate-safe housing town map"></svg>
        <div class="empty-map" id="emptyMap">No towns match the current filters.</div>
      </div>
    </main>

    <aside class="right-panel">
      <h2>Selected Town</h2>
      <section class="profile" id="profile"></section>

      <div class="chart-box">
        <div class="chart-title">Action Category Mix</div>
        <svg id="actionChart" viewBox="0 0 380 190" role="img" aria-label="Action category bar chart"></svg>
      </div>

      <div class="chart-box">
        <div class="chart-title">Housing Need vs MVP Priority</div>
        <svg id="scatterChart" viewBox="0 0 380 260" role="img" aria-label="Housing need scatter plot"></svg>
      </div>

      <h2>Ranked Towns</h2>
      <div class="table-wrap">
        <table class="town-table">
          <thead><tr><th>Town</th><th>County</th><th id="metricHead">Score</th><th>Action</th><th>Assets</th></tr></thead>
          <tbody id="townRows"></tbody>
        </table>
      </div>
    </aside>
  </div>
  <div class="tooltip" id="tooltip"></div>

  <script>
    const DATA = __PAYLOAD__;
    const METRICS = __METRICS__;
    const SVG_WIDTH = 1000;
    const SVG_HEIGHT = 720;
    const PAD = 28;
    const COLORS = ['#f5f1d8', '#c7d99c', '#78b37f', '#2b8c73', '#24536b', '#7f3431'];
    const ACTION_COLORS = {
      'Near-term housing search': '#1f7a5a',
      'Hazard overlay before growth': '#8f3b38',
      'Resilience before or alongside growth': '#24536b',
      'Seasonal market stabilization': '#9a6b23',
      'Infrastructure capacity build-out': '#655d8a',
      'Affordability and parcel screen': '#3f7d8f',
      'Monitor and screen after hazard layers': '#7a8791'
    };

    let state = {
      metric: 'climate_safe_housing_mvp_score',
      county: 'All counties',
      action: 'All actions',
      search: '',
      minMvp: 0,
      minHousing: 0,
      minInfra: 0,
      minResilience: 0,
      maxVulnerability: 100,
      selectedId: null
    };
    let currentBreaks = [];

    const svg = document.getElementById('mapSvg');
    const tooltip = document.getElementById('tooltip');
    const features = DATA.features.map((feature, index) => {
      const p = feature.properties;
      p._id = String(p._id || p.geoid || `${p.town}-${p.county}-${index}`);
      for (const key of Object.keys(METRICS)) p[key] = Number(p[key] || 0);
      [
        'acs_population',
        'pct_cost_burdened_households',
        'pct_cost_burdened_renter_households',
        'pct_below_poverty',
        'pct_zero_vehicle_households',
        'pct_65_plus',
        'pct_with_disability',
        'pct_under_18',
        'pct_seasonal_housing_units',
        'pct_long_commute_workers',
        'pct_no_internet_or_subscription_households',
        'climate_asset_sample_count',
        'bridge_sample_count',
        'culvert_sample_count',
        'slr_site_sample_count',
        'flood_site_sample_count'
      ].forEach((key) => { p[key] = Number(p[key] || 0); });
      return feature;
    });

    function escapeHtml(value) {
      return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    function format(value, digits = 2) {
      return Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: digits });
    }

    function pct(value) {
      return `${format(value, 1)}%`;
    }

    function actionColor(action) {
      return ACTION_COLORS[action] || '#7a8791';
    }

    function filteredFeatures() {
      return features.filter((feature) => {
        const p = feature.properties;
        const countyOk = state.county === 'All counties' || p.county === state.county;
        const actionOk = state.action === 'All actions' || p.primary_action === state.action;
        const textOk = !state.search || `${p.town} ${p.county} ${p.primary_action} ${p.secondary_signals}`.toLowerCase().includes(state.search);
        const scoreOk = p.climate_safe_housing_mvp_score >= state.minMvp
          && p.housing_need_score >= state.minHousing
          && p.infrastructure_efficiency_proxy_score >= state.minInfra
          && p.resilience_investment_priority_score >= state.minResilience
          && p.social_vulnerability_score <= state.maxVulnerability;
        return countyOk && actionOk && textOk && scoreOk;
      });
    }

    function ringsForGeometry(geometry) {
      if (!geometry) return [];
      if (geometry.type === 'Polygon') return geometry.coordinates || [];
      if (geometry.type === 'MultiPolygon') return (geometry.coordinates || []).flat();
      return [];
    }

    function boundsFor(list) {
      let minX = Infinity;
      let minY = Infinity;
      let maxX = -Infinity;
      let maxY = -Infinity;
      for (const feature of list) {
        for (const ring of ringsForGeometry(feature.geometry)) {
          for (const point of ring) {
            const x = Number(point[0]);
            const y = Number(point[1]);
            if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
            minX = Math.min(minX, x);
            minY = Math.min(minY, y);
            maxX = Math.max(maxX, x);
            maxY = Math.max(maxY, y);
          }
        }
      }
      if (!Number.isFinite(minX)) return { minX: -71.2, minY: 42.9, maxX: -66.8, maxY: 47.5 };
      return { minX, minY, maxX, maxY };
    }

    function project(point, box) {
      const width = Math.max(box.maxX - box.minX, 0.000001);
      const height = Math.max(box.maxY - box.minY, 0.000001);
      const scale = Math.min((SVG_WIDTH - PAD * 2) / width, (SVG_HEIGHT - PAD * 2) / height);
      const mapWidth = width * scale;
      const mapHeight = height * scale;
      const offsetX = (SVG_WIDTH - mapWidth) / 2;
      const offsetY = (SVG_HEIGHT - mapHeight) / 2;
      const x = offsetX + (Number(point[0]) - box.minX) * scale;
      const y = offsetY + (box.maxY - Number(point[1])) * scale;
      return [x, y];
    }

    function pathForFeature(feature, box) {
      const parts = [];
      for (const ring of ringsForGeometry(feature.geometry)) {
        if (!ring.length) continue;
        const commands = ring.map((point, index) => {
          const [x, y] = project(point, box);
          return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)} ${y.toFixed(2)}`;
        });
        parts.push(`${commands.join(' ')} Z`);
      }
      return parts.join(' ');
    }

    function valuesFor(metric, list) {
      return list.map((feature) => Number(feature.properties[metric] || 0)).filter(Number.isFinite);
    }

    function quantile(values, q) {
      if (!values.length) return 0;
      const sorted = [...values].sort((a, b) => a - b);
      const position = (sorted.length - 1) * q;
      const lower = Math.floor(position);
      const upper = Math.ceil(position);
      if (lower === upper) return sorted[lower];
      return sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower);
    }

    function metricBreaks(metric, list) {
      if (metric === 'climate_asset_sample_count') return [0, 1, 2, 4, 8];
      const vals = valuesFor(metric, list);
      return [0.15, 0.35, 0.55, 0.72, 0.88].map((q) => quantile(vals, q));
    }

    function colorFor(value) {
      const b = currentBreaks;
      if (value <= b[0]) return COLORS[0];
      if (value <= b[1]) return COLORS[1];
      if (value <= b[2]) return COLORS[2];
      if (value <= b[3]) return COLORS[3];
      if (value <= b[4]) return COLORS[4];
      return COLORS[5];
    }

    function showTooltip(event, feature) {
      const p = feature.properties;
      tooltip.innerHTML = `<strong>${escapeHtml(p.town)}, ${escapeHtml(p.county)}</strong><br>${escapeHtml(METRICS[state.metric])}: ${format(p[state.metric])}<br>${escapeHtml(p.primary_action)}`;
      tooltip.style.display = 'block';
      moveTooltip(event);
    }

    function moveTooltip(event) {
      tooltip.style.left = `${event.clientX + 12}px`;
      tooltip.style.top = `${event.clientY + 12}px`;
    }

    function hideTooltip() {
      tooltip.style.display = 'none';
    }

    function selectFeature(id) {
      state.selectedId = id;
      for (const path of svg.querySelectorAll('path[data-id]')) {
        path.classList.toggle('selected', path.dataset.id === id);
      }
      for (const row of document.querySelectorAll('tr[data-id]')) {
        row.classList.toggle('active', row.dataset.id === id);
      }
      for (const point of document.querySelectorAll('[data-point-id]')) {
        point.setAttribute('stroke-width', point.dataset.pointId === id ? '2.4' : '0.7');
        point.setAttribute('stroke', point.dataset.pointId === id ? '#101820' : '#fff');
      }
      const feature = features.find((item) => item.properties._id === id);
      renderProfile(feature || filteredFeatures()[0] || null);
    }

    function drawMap(list) {
      currentBreaks = metricBreaks(state.metric, list);
      const box = boundsFor(list.length ? list : features);
      svg.innerHTML = '';
      const background = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      background.setAttribute('x', '0');
      background.setAttribute('y', '0');
      background.setAttribute('width', String(SVG_WIDTH));
      background.setAttribute('height', String(SVG_HEIGHT));
      background.setAttribute('fill', '#dbe7e8');
      svg.appendChild(background);

      for (const feature of list) {
        const p = feature.properties;
        const d = pathForFeature(feature, box);
        if (!d) continue;
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', d);
        path.setAttribute('fill', colorFor(Number(p[state.metric] || 0)));
        path.setAttribute('fill-opacity', '0.78');
        path.setAttribute('stroke', state.selectedId === p._id ? '#101820' : '#485661');
        path.setAttribute('stroke-width', state.selectedId === p._id ? '2.8' : '0.7');
        path.setAttribute('fill-rule', 'evenodd');
        path.dataset.id = p._id;
        if (state.selectedId === p._id) path.classList.add('selected');
        path.addEventListener('mouseenter', (event) => showTooltip(event, feature));
        path.addEventListener('mousemove', moveTooltip);
        path.addEventListener('mouseleave', hideTooltip);
        path.addEventListener('click', () => selectFeature(p._id));
        svg.appendChild(path);
      }
      document.getElementById('emptyMap').style.display = list.length ? 'none' : 'block';
    }

    function renderLegend() {
      const b = currentBreaks;
      const labels = [
        `<= ${format(b[0])}`,
        `${format(b[0])} - ${format(b[1])}`,
        `${format(b[1])} - ${format(b[2])}`,
        `${format(b[2])} - ${format(b[3])}`,
        `${format(b[3])} - ${format(b[4])}`,
        `> ${format(b[4])}`
      ];
      document.getElementById('legend').innerHTML = `
        <div class="legend-title">${escapeHtml(METRICS[state.metric])}</div>
        ${COLORS.map((color, index) => `<div class="legend-row"><span class="swatch" style="background:${color}"></span><span>${labels[index]}</span></div>`).join('')}
      `;
    }

    function renderKpis(list) {
      const sorted = [...list].sort((a, b) => Number(b.properties[state.metric] || 0) - Number(a.properties[state.metric] || 0));
      const population = list.reduce((sum, feature) => sum + Number(feature.properties.acs_population || 0), 0);
      const assets = list.reduce((sum, feature) => sum + Number(feature.properties.climate_asset_sample_count || 0), 0);
      const avg = list.length ? valuesFor(state.metric, list).reduce((sum, value) => sum + value, 0) / list.length : 0;
      const highHousing = list.filter((feature) => feature.properties.housing_need_score >= 60).length;
      document.getElementById('townCount').textContent = list.length.toLocaleString();
      document.getElementById('populationCount').textContent = Math.round(population).toLocaleString();
      document.getElementById('topTown').textContent = sorted[0] ? sorted[0].properties.town : '-';
      document.getElementById('avgMetric').textContent = format(avg);
      document.getElementById('highHousing').textContent = highHousing.toLocaleString();
      document.getElementById('assetTotal').textContent = Math.round(assets).toLocaleString();
      document.getElementById('filterSummary').textContent = `${list.length.toLocaleString()} town(s) | ${METRICS[state.metric]}`;
      document.getElementById('metricHead').textContent = METRICS[state.metric];
    }

    function detailRow(label, value) {
      return `<tr><td>${escapeHtml(label)}</td><td>${escapeHtml(value)}</td></tr>`;
    }

    function renderProfile(feature) {
      const panel = document.getElementById('profile');
      if (!feature) {
        panel.innerHTML = '<div class="profile-title">No town selected</div><div class="profile-note">Adjust filters or select a town from the map, chart, or table.</div>';
        return;
      }
      const p = feature.properties;
      const drivers = Array.isArray(p.key_drivers) ? p.key_drivers.join(', ') : (p.key_drivers || '');
      panel.innerHTML = `
        <div class="profile-title">${escapeHtml(p.town)}, ${escapeHtml(p.county)}</div>
        <span class="pill" style="background:${actionColor(p.primary_action)}">${escapeHtml(p.primary_action)}</span>
        <div class="profile-note">${escapeHtml(p.decision_note || '')}</div>
        <table class="detail-table">
          ${detailRow(METRICS[state.metric], format(p[state.metric]))}
          ${detailRow('MVP search priority', format(p.climate_safe_housing_mvp_score))}
          ${detailRow('Housing need', format(p.housing_need_score))}
          ${detailRow('Social vulnerability', format(p.social_vulnerability_score))}
          ${detailRow('Infrastructure proxy', format(p.infrastructure_efficiency_proxy_score))}
          ${detailRow('Resilience priority', format(p.resilience_investment_priority_score))}
          ${detailRow('Population', format(p.acs_population, 0))}
          ${detailRow('Cost burden', pct(p.pct_cost_burdened_households))}
          ${detailRow('Renter burden', pct(p.pct_cost_burdened_renter_households))}
          ${detailRow('Seasonal housing', pct(p.pct_seasonal_housing_units))}
          ${detailRow('Long commute', pct(p.pct_long_commute_workers))}
          ${detailRow('No internet/subscription', pct(p.pct_no_internet_or_subscription_households))}
          ${detailRow('Sample climate assets', format(p.climate_asset_sample_count, 0))}
          ${detailRow('Key drivers', drivers)}
          ${detailRow('Signals', p.secondary_signals || '')}
        </table>`;
    }

    function renderTownRows(list) {
      const sorted = [...list].sort((a, b) => Number(b.properties[state.metric] || 0) - Number(a.properties[state.metric] || 0));
      document.getElementById('townRows').innerHTML = sorted.slice(0, 80).map((feature) => {
        const p = feature.properties;
        const active = p._id === state.selectedId ? ' class="active"' : '';
        return `<tr data-id="${escapeHtml(p._id)}"${active}>
          <td><strong>${escapeHtml(p.town)}</strong></td>
          <td>${escapeHtml(p.county)}</td>
          <td>${format(p[state.metric])}</td>
          <td>${escapeHtml(p.primary_action)}</td>
          <td>${format(p.climate_asset_sample_count, 0)}</td>
        </tr>`;
      }).join('');
      for (const row of document.querySelectorAll('tr[data-id]')) {
        row.addEventListener('click', () => selectFeature(row.dataset.id));
      }
    }

    function renderActionChart(list) {
      const svgChart = document.getElementById('actionChart');
      const counts = new Map();
      for (const feature of list) {
        const action = feature.properties.primary_action || 'Monitor and screen after hazard layers';
        counts.set(action, (counts.get(action) || 0) + 1);
      }
      const rows = Array.from(counts.entries()).sort((a, b) => b[1] - a[1]).slice(0, 7);
      const max = Math.max(1, ...rows.map((row) => row[1]));
      svgChart.innerHTML = '';
      rows.forEach(([action, count], index) => {
        const y = 18 + index * 23;
        const width = 210 * count / max;
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.style.cursor = 'pointer';
        group.addEventListener('click', () => {
          state.action = action;
          document.getElementById('actionSelect').value = action;
          renderAll();
        });
        group.innerHTML = `
          <rect x="152" y="${y - 11}" width="${width.toFixed(1)}" height="14" rx="2" fill="${actionColor(action)}"></rect>
          <text x="0" y="${y}" font-size="10" fill="#34444f">${escapeHtml(action.slice(0, 27))}</text>
          <text x="${Math.min(370, 158 + width)}" y="${y}" font-size="10" font-weight="700" fill="#17202a">${count}</text>`;
        svgChart.appendChild(group);
      });
    }

    function renderScatter(list) {
      const chart = document.getElementById('scatterChart');
      chart.innerHTML = '';
      const margin = { left: 42, top: 16, right: 14, bottom: 34 };
      const w = 380 - margin.left - margin.right;
      const h = 260 - margin.top - margin.bottom;
      const x = (value) => margin.left + (Number(value || 0) / 100) * w;
      const y = (value) => margin.top + h - (Number(value || 0) / 100) * h;
      const axis = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      axis.innerHTML = `
        <line x1="${margin.left}" y1="${margin.top + h}" x2="${margin.left + w}" y2="${margin.top + h}" stroke="#82919c" stroke-width="1"></line>
        <line x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${margin.top + h}" stroke="#82919c" stroke-width="1"></line>
        <text x="${margin.left + w / 2}" y="252" font-size="10" text-anchor="middle" fill="#617080">Housing Need</text>
        <text transform="translate(12 ${margin.top + h / 2}) rotate(-90)" font-size="10" text-anchor="middle" fill="#617080">MVP Priority</text>
      `;
      chart.appendChild(axis);
      [25, 50, 75].forEach((tick) => {
        const grid = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        grid.innerHTML = `
          <line x1="${x(tick)}" y1="${margin.top}" x2="${x(tick)}" y2="${margin.top + h}" stroke="#e1e8ed"></line>
          <line x1="${margin.left}" y1="${y(tick)}" x2="${margin.left + w}" y2="${y(tick)}" stroke="#e1e8ed"></line>`;
        chart.appendChild(grid);
      });
      for (const feature of list) {
        const p = feature.properties;
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        const radius = Math.max(3, Math.min(8, Math.sqrt(p.acs_population || 1) / 36));
        circle.setAttribute('cx', x(p.housing_need_score));
        circle.setAttribute('cy', y(p.climate_safe_housing_mvp_score));
        circle.setAttribute('r', radius.toFixed(1));
        circle.setAttribute('fill', actionColor(p.primary_action));
        circle.setAttribute('fill-opacity', '0.78');
        circle.setAttribute('stroke', p._id === state.selectedId ? '#101820' : '#fff');
        circle.setAttribute('stroke-width', p._id === state.selectedId ? '2.4' : '0.7');
        circle.dataset.pointId = p._id;
        circle.style.cursor = 'pointer';
        circle.addEventListener('mouseenter', (event) => showTooltip(event, feature));
        circle.addEventListener('mousemove', moveTooltip);
        circle.addEventListener('mouseleave', hideTooltip);
        circle.addEventListener('click', () => selectFeature(p._id));
        chart.appendChild(circle);
      }
    }

    function renderControls() {
      const counties = ['All counties', ...Array.from(new Set(features.map((feature) => feature.properties.county))).sort()];
      document.getElementById('countySelect').innerHTML = counties.map((county) => `<option value="${escapeHtml(county)}">${escapeHtml(county)}</option>`).join('');
      const actions = ['All actions', ...Array.from(new Set(features.map((feature) => feature.properties.primary_action))).sort()];
      document.getElementById('actionSelect').innerHTML = actions.map((action) => `<option value="${escapeHtml(action)}">${escapeHtml(action)}</option>`).join('');
    }

    function syncRangeLabels() {
      document.getElementById('mvpValue').textContent = state.minMvp;
      document.getElementById('housingValue').textContent = state.minHousing;
      document.getElementById('infraValue').textContent = state.minInfra;
      document.getElementById('resilienceValue').textContent = state.minResilience;
      document.getElementById('vulnerabilityValue').textContent = state.maxVulnerability;
    }

    function renderAll() {
      syncRangeLabels();
      const list = filteredFeatures();
      if (state.selectedId && !list.some((feature) => feature.properties._id === state.selectedId)) {
        state.selectedId = null;
      }
      drawMap(list);
      renderLegend();
      renderKpis(list);
      renderTownRows(list);
      renderActionChart(list);
      renderScatter(list);
      const selected = state.selectedId
        ? features.find((feature) => feature.properties._id === state.selectedId)
        : list[0];
      if (selected && !state.selectedId) state.selectedId = selected.properties._id;
      selectFeature(state.selectedId);
    }

    renderControls();
    document.getElementById('metricSelect').addEventListener('change', (event) => { state.metric = event.target.value; renderAll(); });
    document.getElementById('countySelect').addEventListener('change', (event) => { state.county = event.target.value; renderAll(); });
    document.getElementById('actionSelect').addEventListener('change', (event) => { state.action = event.target.value; renderAll(); });
    document.getElementById('searchBox').addEventListener('input', (event) => { state.search = event.target.value.trim().toLowerCase(); renderAll(); });
    document.getElementById('mvpRange').addEventListener('input', (event) => { state.minMvp = Number(event.target.value); renderAll(); });
    document.getElementById('housingRange').addEventListener('input', (event) => { state.minHousing = Number(event.target.value); renderAll(); });
    document.getElementById('infraRange').addEventListener('input', (event) => { state.minInfra = Number(event.target.value); renderAll(); });
    document.getElementById('resilienceRange').addEventListener('input', (event) => { state.minResilience = Number(event.target.value); renderAll(); });
    document.getElementById('vulnerabilityRange').addEventListener('input', (event) => { state.maxVulnerability = Number(event.target.value); renderAll(); });
    document.getElementById('resetButton').addEventListener('click', () => {
      state = {
        metric: 'climate_safe_housing_mvp_score',
        county: 'All counties',
        action: 'All actions',
        search: '',
        minMvp: 0,
        minHousing: 0,
        minInfra: 0,
        minResilience: 0,
        maxVulnerability: 100,
        selectedId: null
      };
      document.getElementById('metricSelect').value = state.metric;
      document.getElementById('countySelect').value = state.county;
      document.getElementById('actionSelect').value = state.action;
      document.getElementById('searchBox').value = '';
      document.getElementById('mvpRange').value = '0';
      document.getElementById('housingRange').value = '0';
      document.getElementById('infraRange').value = '0';
      document.getElementById('resilienceRange').value = '0';
      document.getElementById('vulnerabilityRange').value = '100';
      renderAll();
    });
    renderAll();
  </script>
</body>
</html>
"""
    return (
        html.replace("__PAYLOAD__", data)
        .replace("__METRICS__", metrics)
        .replace("__METRIC_OPTIONS__", metric_options)
    )


def write_app(config_path: str = "configs/project.toml") -> Path:
    cfg = load_config(config_path)
    ensure_directories(cfg)
    payload = load_payload(cfg)
    path = resolve_path(cfg, "reports_dir") / "climate_housing_intelligence_app.html"
    path.write_text(build_html(payload), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the synchronized climate-safe housing dashboard app.")
    parser.add_argument("--config", default="configs/project.toml")
    args = parser.parse_args()
    print(write_app(args.config))


if __name__ == "__main__":
    main()
