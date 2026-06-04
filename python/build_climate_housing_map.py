from __future__ import annotations

import argparse
import json
from pathlib import Path

from config import ensure_directories, load_config, resolve_path


METRICS = {
    "climate_safe_housing_mvp_score": "MVP Search Priority",
    "housing_need_score": "Housing Need",
    "social_vulnerability_score": "Social Vulnerability",
    "infrastructure_efficiency_proxy_score": "Infrastructure Proxy",
    "resilience_investment_priority_score": "Resilience Priority",
    "climate_asset_sample_count": "Sample Climate Assets",
}


def load_geojson(cfg: dict) -> dict:
    path = resolve_path(cfg, "reports_dir") / "climate_safe_housing_town_screening.geojson"
    return json.loads(path.read_text(encoding="utf-8"))


def build_html(geojson: dict) -> str:
    payload = json.dumps(geojson, separators=(",", ":"))
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
  <title>Maine Climate-Safe Housing Map</title>
  <style>
    :root {
      --ink: #17202a;
      --muted: #66737f;
      --line: #d8e0e6;
      --panel: #ffffff;
      --page: #edf1f3;
      --accent: #1f7a5a;
      --accent-dark: #123f36;
      --warning: #8f5b25;
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
      grid-template-columns: minmax(320px, 390px) minmax(0, 1fr);
      height: 100vh;
    }
    aside {
      background: var(--panel);
      border-right: 1px solid var(--line);
      padding: 16px;
      overflow: auto;
      z-index: 3;
    }
    .map-shell {
      position: relative;
      min-height: 100vh;
      background: #e6ecef;
      overflow: hidden;
    }
    #mapSvg {
      width: 100%;
      height: 100%;
      display: block;
      background:
        linear-gradient(0deg, rgba(255,255,255,0.35), rgba(255,255,255,0.35)),
        #dbe7e8;
    }
    #mapSvg path {
      cursor: pointer;
      vector-effect: non-scaling-stroke;
      transition: fill-opacity 120ms ease, stroke-width 120ms ease;
    }
    #mapSvg path:hover {
      fill-opacity: 0.9;
      stroke-width: 1.7;
    }
    #mapSvg path.selected {
      stroke: var(--selected);
      stroke-width: 2.4;
      fill-opacity: 0.92;
    }
    h1 {
      margin: 0 0 6px;
      font-size: 20px;
      line-height: 1.18;
      color: var(--accent-dark);
      letter-spacing: 0;
    }
    .subtitle {
      margin: 0 0 14px;
      font-size: 12px;
      line-height: 1.35;
      color: var(--muted);
    }
    .control { margin: 12px 0; }
    label {
      display: block;
      font-size: 11px;
      font-weight: 700;
      color: #3f4b56;
      margin-bottom: 5px;
      text-transform: uppercase;
      letter-spacing: 0;
    }
    select,
    input {
      width: 100%;
      height: 36px;
      border: 1px solid #cbd5dd;
      border-radius: 4px;
      padding: 0 10px;
      font-size: 13px;
      color: var(--ink);
      background: #fff;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin: 14px 0;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #fbfcfd;
      min-height: 72px;
    }
    .metric .label {
      font-size: 10px;
      color: var(--muted);
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0;
    }
    .metric .value {
      margin-top: 6px;
      font-size: 20px;
      font-weight: 800;
      color: #173f34;
      line-height: 1.1;
      overflow-wrap: anywhere;
    }
    .section-title {
      margin: 18px 0 8px;
      font-size: 12px;
      font-weight: 800;
      color: #23313d;
      text-transform: uppercase;
      letter-spacing: 0;
    }
    .town-list {
      display: grid;
      gap: 7px;
    }
    .town-row {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 9px;
      background: #fff;
      cursor: pointer;
    }
    .town-row:hover,
    .town-row.active {
      border-color: #7da390;
      background: #f5fbf8;
    }
    .town-main {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      font-size: 13px;
      font-weight: 800;
    }
    .town-sub {
      margin-top: 4px;
      font-size: 11px;
      line-height: 1.35;
      color: var(--muted);
    }
    .detail {
      position: absolute;
      right: 18px;
      top: 18px;
      width: min(360px, calc(100% - 36px));
      background: rgba(255,255,255,0.96);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      box-shadow: 0 10px 24px rgba(23, 32, 42, 0.16);
      z-index: 2;
    }
    .detail-title {
      font-size: 15px;
      font-weight: 800;
      color: var(--accent-dark);
      margin-bottom: 6px;
    }
    .detail-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
    }
    .detail-table td {
      border-bottom: 1px solid #e6ebef;
      padding: 5px 0;
      vertical-align: top;
    }
    .detail-table td:last-child {
      text-align: right;
      font-weight: 700;
      padding-left: 12px;
    }
    .legend {
      position: absolute;
      right: 18px;
      bottom: 18px;
      z-index: 2;
      background: rgba(255,255,255,0.96);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      min-width: 180px;
      box-shadow: 0 10px 24px rgba(23, 32, 42, 0.14);
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
    .source {
      margin-top: 16px;
      padding-top: 12px;
      border-top: 1px solid var(--line);
      font-size: 11px;
      line-height: 1.35;
      color: var(--muted);
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
      max-width: 240px;
    }
    @media (max-width: 860px) {
      body { overflow: auto; }
      .app {
        grid-template-columns: 1fr;
        grid-template-rows: 52vh auto;
        height: auto;
      }
      aside {
        grid-row: 2;
        border-right: 0;
        border-top: 1px solid var(--line);
        max-height: none;
      }
      .map-shell {
        grid-row: 1;
        min-height: 52vh;
      }
      .detail {
        left: 8px;
        right: 8px;
        top: 8px;
        width: auto;
        max-height: 38vh;
        overflow: auto;
      }
      .legend {
        right: 8px;
        bottom: 8px;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <h1>Maine Climate-Safe Housing Screening</h1>
      <p class="subtitle">Town-level MVP map from ACS housing, vulnerability, commute, digital access, and sampled climate infrastructure data.</p>

      <div class="control">
        <label for="metricSelect">Layer</label>
        <select id="metricSelect">__METRIC_OPTIONS__</select>
      </div>
      <div class="control">
        <label for="countySelect">County</label>
        <select id="countySelect"></select>
      </div>
      <div class="control">
        <label for="searchBox">Town Search</label>
        <input id="searchBox" type="search" placeholder="Portland, Brunswick, Kennebunk">
      </div>

      <div class="cards">
        <div class="metric"><div class="label">Towns Shown</div><div class="value" id="townCount">0</div></div>
        <div class="metric"><div class="label">Top Town</div><div class="value" id="topTown">-</div></div>
        <div class="metric"><div class="label">Median Score</div><div class="value" id="medianScore">0</div></div>
        <div class="metric"><div class="label">Climate Assets</div><div class="value" id="assetCount">0</div></div>
      </div>

      <div class="section-title">Highest Ranked Towns</div>
      <div class="town-list" id="townList"></div>

      <div class="source">
        Geometry: Census TIGER/Line 2024 county subdivisions. Scores are MVP screening values. Full FEMA/MGS/wetlands/conservation/DEM overlays are pending before parcel-level climate-safe conclusions.
      </div>
    </aside>
    <main class="map-shell">
      <svg id="mapSvg" viewBox="0 0 1000 720" role="img" aria-label="Maine town screening map"></svg>
      <section class="detail" id="detailPanel"></section>
      <section class="legend" id="legend"></section>
    </main>
  </div>
  <div class="tooltip" id="tooltip"></div>

  <script>
    const DATA = __PAYLOAD__;
    const METRICS = __METRICS__;
    const COLORS = ['#f5f1d8', '#c7d99c', '#78b37f', '#2b8c73', '#24536b', '#7f3431'];
    const SVG_WIDTH = 1000;
    const SVG_HEIGHT = 720;
    const PAD = 28;

    let activeMetric = 'climate_safe_housing_mvp_score';
    let activeCounty = 'All counties';
    let searchText = '';
    let selectedGeoid = null;
    let currentBreaks = [];

    const svg = document.getElementById('mapSvg');
    const tooltip = document.getElementById('tooltip');
    const features = DATA.features.map((feature) => {
      const p = feature.properties;
      for (const key of Object.keys(METRICS)) {
        p[key] = Number(p[key] || 0);
      }
      p.acs_population = Number(p.acs_population || 0);
      p.climate_asset_sample_count = Number(p.climate_asset_sample_count || 0);
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

    function filteredFeatures() {
      return features.filter((feature) => {
        const p = feature.properties;
        const countyOk = activeCounty === 'All counties' || p.county === activeCounty;
        const textOk = !searchText || `${p.town} ${p.county}`.toLowerCase().includes(searchText);
        return countyOk && textOk;
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

    function valuesFor(metric, list = filteredFeatures()) {
      return list
        .map((feature) => Number(feature.properties[metric] || 0))
        .filter((value) => Number.isFinite(value));
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
      const vals = valuesFor(metric, list);
      if (metric === 'climate_asset_sample_count') return [0, 1, 2, 4, 8];
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

    function format(value) {
      const num = Number(value || 0);
      return num.toLocaleString(undefined, { maximumFractionDigits: 2 });
    }

    function driverText(p) {
      return Array.isArray(p.key_drivers) ? p.key_drivers.join(', ') : (p.key_drivers || '');
    }

    function detailHtml(feature) {
      if (!feature) {
        return `
          <div class="detail-title">Maine town screening map</div>
          <table class="detail-table">
            <tr><td>Current layer</td><td>${escapeHtml(METRICS[activeMetric])}</td></tr>
            <tr><td>Visible towns</td><td>${filteredFeatures().length.toLocaleString()}</td></tr>
            <tr><td>Status</td><td>Ready</td></tr>
          </table>`;
      }
      const p = feature.properties;
      return `
        <div class="detail-title">${escapeHtml(p.town)}, ${escapeHtml(p.county)}</div>
        <table class="detail-table">
          <tr><td>${escapeHtml(METRICS[activeMetric])}</td><td>${format(p[activeMetric])}</td></tr>
          <tr><td>MVP score</td><td>${format(p.climate_safe_housing_mvp_score)}</td></tr>
          <tr><td>Housing need</td><td>${format(p.housing_need_score)}</td></tr>
          <tr><td>Social vulnerability</td><td>${format(p.social_vulnerability_score)}</td></tr>
          <tr><td>Resilience priority</td><td>${format(p.resilience_investment_priority_score)}</td></tr>
          <tr><td>Population</td><td>${format(p.acs_population)}</td></tr>
          <tr><td>Sample climate assets</td><td>${format(p.climate_asset_sample_count)}</td></tr>
          <tr><td>Lane</td><td>${escapeHtml(p.mvp_priority_lane || '')}</td></tr>
          <tr><td>Key drivers</td><td>${escapeHtml(driverText(p))}</td></tr>
        </table>`;
    }

    function showDetail(feature) {
      document.getElementById('detailPanel').innerHTML = detailHtml(feature);
    }

    function showTooltip(event, feature) {
      const p = feature.properties;
      tooltip.innerHTML = `<strong>${escapeHtml(p.town)}, ${escapeHtml(p.county)}</strong><br>${escapeHtml(METRICS[activeMetric])}: ${format(p[activeMetric])}`;
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

    function selectFeature(geoid, focusSidebar = true) {
      selectedGeoid = geoid;
      for (const path of svg.querySelectorAll('path[data-geoid]')) {
        path.classList.toggle('selected', path.dataset.geoid === geoid);
      }
      for (const row of document.querySelectorAll('.town-row')) {
        row.classList.toggle('active', row.dataset.geoid === geoid);
      }
      const feature = features.find((item) => item.properties.geoid === geoid);
      showDetail(feature);
      if (focusSidebar) {
        const active = Array.from(document.querySelectorAll('.town-row'))
          .find((row) => row.dataset.geoid === geoid);
        if (active) active.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    }

    function drawMap() {
      const list = filteredFeatures();
      const box = boundsFor(list.length ? list : features);
      currentBreaks = metricBreaks(activeMetric, list);
      svg.innerHTML = '';

      const background = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      background.setAttribute('x', '0');
      background.setAttribute('y', '0');
      background.setAttribute('width', String(SVG_WIDTH));
      background.setAttribute('height', String(SVG_HEIGHT));
      background.setAttribute('fill', '#dbe7e8');
      svg.appendChild(background);

      for (const feature of list) {
        const d = pathForFeature(feature, box);
        if (!d) continue;
        const p = feature.properties;
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', d);
        path.setAttribute('fill', colorFor(Number(p[activeMetric] || 0)));
        path.setAttribute('fill-opacity', '0.76');
        path.setAttribute('stroke', '#46515c');
        path.setAttribute('stroke-width', '0.7');
        path.dataset.geoid = p.geoid;
        path.addEventListener('mouseenter', (event) => {
          showTooltip(event, feature);
          showDetail(feature);
        });
        path.addEventListener('mousemove', moveTooltip);
        path.addEventListener('mouseleave', () => {
          hideTooltip();
          if (selectedGeoid) {
            const selected = features.find((item) => item.properties.geoid === selectedGeoid);
            showDetail(selected);
          }
        });
        path.addEventListener('click', () => selectFeature(p.geoid));
        svg.appendChild(path);
      }

      if (selectedGeoid && list.some((feature) => feature.properties.geoid === selectedGeoid)) {
        selectFeature(selectedGeoid, false);
      } else {
        selectedGeoid = null;
        showDetail(list[0] || null);
      }
      updateSidebar(list);
      updateLegend();
    }

    function updateSidebar(list) {
      const sorted = [...list].sort((a, b) => Number(b.properties[activeMetric] || 0) - Number(a.properties[activeMetric] || 0));
      const vals = valuesFor(activeMetric, list).sort((a, b) => a - b);
      const median = vals.length ? vals[Math.floor(vals.length / 2)] : 0;
      const assets = list.reduce((sum, feature) => sum + Number(feature.properties.climate_asset_sample_count || 0), 0);
      document.getElementById('townCount').textContent = list.length.toLocaleString();
      document.getElementById('topTown').textContent = sorted[0] ? sorted[0].properties.town : '-';
      document.getElementById('medianScore').textContent = format(median);
      document.getElementById('assetCount').textContent = assets.toLocaleString();

      const townList = document.getElementById('townList');
      townList.innerHTML = sorted.slice(0, 14).map((feature, index) => {
        const p = feature.properties;
        const drivers = Array.isArray(p.key_drivers) ? p.key_drivers.slice(0, 3).join(', ') : p.key_drivers;
        const active = p.geoid === selectedGeoid ? ' active' : '';
        return `<div class="town-row${active}" data-geoid="${escapeHtml(p.geoid)}">
          <div class="town-main"><span>${index + 1}. ${escapeHtml(p.town)}</span><span>${format(p[activeMetric])}</span></div>
          <div class="town-sub">${escapeHtml(p.county)} County - ${escapeHtml(drivers || '')}</div>
        </div>`;
      }).join('');
      for (const row of townList.querySelectorAll('.town-row')) {
        row.addEventListener('click', () => selectFeature(row.dataset.geoid, false));
      }
    }

    function updateLegend() {
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
        <div class="legend-title">${escapeHtml(METRICS[activeMetric])}</div>
        ${COLORS.map((color, index) => `<div class="legend-row"><span class="swatch" style="background:${color}"></span><span>${labels[index]}</span></div>`).join('')}
      `;
    }

    function populateCounties() {
      const counties = ['All counties', ...Array.from(new Set(features.map((feature) => feature.properties.county))).sort()];
      const select = document.getElementById('countySelect');
      select.innerHTML = counties.map((county) => `<option value="${escapeHtml(county)}">${escapeHtml(county)}</option>`).join('');
    }

    populateCounties();
    document.getElementById('metricSelect').addEventListener('change', (event) => {
      activeMetric = event.target.value;
      drawMap();
    });
    document.getElementById('countySelect').addEventListener('change', (event) => {
      activeCounty = event.target.value;
      drawMap();
    });
    document.getElementById('searchBox').addEventListener('input', (event) => {
      searchText = event.target.value.trim().toLowerCase();
      drawMap();
    });
    drawMap();
  </script>
</body>
</html>
"""
    return (
        html.replace("__PAYLOAD__", payload)
        .replace("__METRICS__", metrics)
        .replace("__METRIC_OPTIONS__", metric_options)
    )


def write_map(config_path: str = "configs/project.toml") -> Path:
    cfg = load_config(config_path)
    ensure_directories(cfg)
    geojson = load_geojson(cfg)
    path = resolve_path(cfg, "reports_dir") / "climate_safe_housing_interactive_map.html"
    path.write_text(build_html(geojson), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a standalone interactive map for climate-safe housing screening.")
    parser.add_argument("--config", default="configs/project.toml")
    args = parser.parse_args()
    print(write_map(args.config))


if __name__ == "__main__":
    main()
