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
    metric_options = "\n".join(
        f'<option value="{key}">{label}</option>'
        for key, label in METRICS.items()
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Maine Climate-Safe Housing Map</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    integrity="sha256-p4NxAoJBhIINfQ40rjDsQEV78P6lm/FKQNAJQ3sQ0kM=" crossorigin="">
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
    integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
  <style>
    :root {{
      --ink: #17202a;
      --muted: #64707d;
      --line: #d9e0e7;
      --panel: #ffffff;
      --page: #eef2f4;
      --accent: #1f7a5a;
      --warn: #b45f06;
      --risk: #a93226;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      height: 100vh;
      overflow: hidden;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--ink);
      background: var(--page);
    }}
    .app {{
      display: grid;
      grid-template-columns: minmax(320px, 390px) minmax(0, 1fr);
      height: 100vh;
    }}
    aside {{
      background: var(--panel);
      border-right: 1px solid var(--line);
      padding: 16px;
      overflow: auto;
    }}
    #map {{ min-height: 100vh; background: #e6ecef; }}
    h1 {{
      margin: 0 0 6px;
      font-size: 20px;
      line-height: 1.18;
      color: #123f36;
      letter-spacing: 0;
    }}
    .subtitle {{
      margin: 0 0 14px;
      font-size: 12px;
      line-height: 1.35;
      color: var(--muted);
    }}
    .control {{
      margin: 12px 0;
    }}
    label {{
      display: block;
      font-size: 11px;
      font-weight: 700;
      color: #3f4b56;
      margin-bottom: 5px;
      text-transform: uppercase;
      letter-spacing: 0;
    }}
    select, input {{
      width: 100%;
      height: 36px;
      border: 1px solid #cbd5dd;
      border-radius: 4px;
      padding: 0 10px;
      font-size: 13px;
      color: var(--ink);
      background: #fff;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin: 14px 0;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #fbfcfd;
      min-height: 72px;
    }}
    .metric .label {{
      font-size: 10px;
      color: var(--muted);
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .metric .value {{
      margin-top: 6px;
      font-size: 20px;
      font-weight: 800;
      color: #173f34;
      line-height: 1.1;
    }}
    .section-title {{
      margin: 18px 0 8px;
      font-size: 12px;
      font-weight: 800;
      color: #23313d;
      text-transform: uppercase;
      letter-spacing: 0;
    }}
    .town-list {{
      display: grid;
      gap: 7px;
    }}
    .town-row {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 9px;
      background: #fff;
      cursor: pointer;
    }}
    .town-row:hover {{ border-color: #8da99b; background: #f7fbf9; }}
    .town-main {{
      display: flex;
      justify-content: space-between;
      gap: 8px;
      font-size: 13px;
      font-weight: 800;
    }}
    .town-sub {{
      margin-top: 4px;
      font-size: 11px;
      line-height: 1.35;
      color: var(--muted);
    }}
    .legend {{
      position: absolute;
      right: 18px;
      bottom: 18px;
      z-index: 600;
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      min-width: 180px;
      box-shadow: 0 10px 24px rgba(23, 32, 42, 0.14);
    }}
    .legend-title {{
      font-size: 11px;
      font-weight: 800;
      margin-bottom: 8px;
      color: #23313d;
    }}
    .legend-row {{
      display: grid;
      grid-template-columns: 18px 1fr;
      gap: 8px;
      align-items: center;
      font-size: 11px;
      color: #3f4b56;
      margin: 5px 0;
    }}
    .swatch {{
      width: 18px;
      height: 12px;
      border: 1px solid rgba(0,0,0,0.18);
    }}
    .popup-title {{
      font-size: 15px;
      font-weight: 800;
      margin-bottom: 4px;
    }}
    .popup-table {{
      border-collapse: collapse;
      width: 260px;
      font-size: 11px;
    }}
    .popup-table td {{
      border-bottom: 1px solid #e6ebef;
      padding: 4px 0;
      vertical-align: top;
    }}
    .popup-table td:last-child {{
      text-align: right;
      font-weight: 700;
    }}
    .source {{
      margin-top: 16px;
      padding-top: 12px;
      border-top: 1px solid var(--line);
      font-size: 11px;
      line-height: 1.35;
      color: var(--muted);
    }}
    @media (max-width: 820px) {{
      body {{ overflow: auto; }}
      .app {{ grid-template-columns: 1fr; grid-template-rows: 46vh auto; height: auto; }}
      aside {{ grid-row: 2; border-right: 0; border-top: 1px solid var(--line); max-height: none; }}
      #map {{ grid-row: 1; min-height: 46vh; }}
      .legend {{ right: 8px; bottom: 8px; }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <h1>Maine Climate-Safe Housing Screening</h1>
      <p class="subtitle">Town-level MVP map from ACS housing, vulnerability, commute, digital access, and sampled climate infrastructure data.</p>

      <div class="control">
        <label for="metricSelect">Layer</label>
        <select id="metricSelect">{metric_options}</select>
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
    <main id="map"></main>
  </div>
  <div class="legend" id="legend"></div>

  <script>
    const DATA = {payload};
    const METRICS = {json.dumps(METRICS, separators=(",", ":"))};
    const COLORS = ['#f5f1d8', '#cbd99f', '#78b37f', '#2b8c73', '#24536b', '#7f3431'];
    const map = L.map('map', {{ zoomControl: true, preferCanvas: true }}).setView([45.25, -69.2], 7);
    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
      maxZoom: 18,
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
    }}).addTo(map);

    let activeMetric = 'climate_safe_housing_mvp_score';
    let activeCounty = 'All counties';
    let searchText = '';
    let geoLayer = null;
    let selectedLayer = null;

    const features = DATA.features.map((feature) => {{
      const p = feature.properties;
      for (const key of Object.keys(METRICS)) {{
        p[key] = Number(p[key] || 0);
      }}
      p.acs_population = Number(p.acs_population || 0);
      p.climate_asset_sample_count = Number(p.climate_asset_sample_count || 0);
      return feature;
    }});

    function filteredFeatures() {{
      return features.filter((feature) => {{
        const p = feature.properties;
        const countyOk = activeCounty === 'All counties' || p.county === activeCounty;
        const textOk = !searchText || `${{p.town}} ${{p.county}}`.toLowerCase().includes(searchText);
        return countyOk && textOk;
      }});
    }}

    function valuesFor(metric, list = filteredFeatures()) {{
      return list.map((feature) => Number(feature.properties[metric] || 0)).filter((value) => Number.isFinite(value));
    }}

    function quantile(values, q) {{
      if (!values.length) return 0;
      const sorted = [...values].sort((a, b) => a - b);
      const position = (sorted.length - 1) * q;
      const lower = Math.floor(position);
      const upper = Math.ceil(position);
      if (lower === upper) return sorted[lower];
      return sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower);
    }}

    function breaks(metric) {{
      const vals = valuesFor(metric);
      if (metric === 'climate_asset_sample_count') {{
        return [0, 1, 2, 4, 8];
      }}
      return [0.15, 0.35, 0.55, 0.72, 0.88].map((q) => quantile(vals, q));
    }}

    function colorFor(value, metric) {{
      const b = breaks(metric);
      if (value <= b[0]) return COLORS[0];
      if (value <= b[1]) return COLORS[1];
      if (value <= b[2]) return COLORS[2];
      if (value <= b[3]) return COLORS[3];
      if (value <= b[4]) return COLORS[4];
      return COLORS[5];
    }}

    function styleFeature(feature) {{
      const value = Number(feature.properties[activeMetric] || 0);
      return {{
        color: '#46515c',
        weight: 0.75,
        opacity: 0.85,
        fillColor: colorFor(value, activeMetric),
        fillOpacity: 0.74
      }};
    }}

    function format(value) {{
      const num = Number(value || 0);
      return num.toLocaleString(undefined, {{ maximumFractionDigits: 2 }});
    }}

    function popupHtml(p) {{
      const drivers = Array.isArray(p.key_drivers) ? p.key_drivers.join(', ') : p.key_drivers;
      return `
        <div class="popup-title">${{p.town}}, ${{p.county}}</div>
        <table class="popup-table">
          <tr><td>${{METRICS[activeMetric]}}</td><td>${{format(p[activeMetric])}}</td></tr>
          <tr><td>MVP score</td><td>${{format(p.climate_safe_housing_mvp_score)}}</td></tr>
          <tr><td>Housing need</td><td>${{format(p.housing_need_score)}}</td></tr>
          <tr><td>Social vulnerability</td><td>${{format(p.social_vulnerability_score)}}</td></tr>
          <tr><td>Resilience priority</td><td>${{format(p.resilience_investment_priority_score)}}</td></tr>
          <tr><td>Population</td><td>${{format(p.acs_population)}}</td></tr>
          <tr><td>Sample climate assets</td><td>${{format(p.climate_asset_sample_count)}}</td></tr>
          <tr><td>Lane</td><td>${{p.mvp_priority_lane || ''}}</td></tr>
          <tr><td>Key drivers</td><td>${{drivers || ''}}</td></tr>
        </table>`;
    }}

    function onEachFeature(feature, layer) {{
      const p = feature.properties;
      layer.bindTooltip(`${{p.town}}, ${{p.county}}<br>${{METRICS[activeMetric]}}: ${{format(p[activeMetric])}}`, {{
        sticky: true,
        direction: 'top'
      }});
      layer.bindPopup(popupHtml(p));
      layer.on('click', () => {{
        if (selectedLayer) geoLayer.resetStyle(selectedLayer);
        selectedLayer = layer;
        layer.setStyle({{ weight: 2.4, color: '#1f2933', fillOpacity: 0.88 }});
      }});
    }}

    function drawMap() {{
      if (geoLayer) geoLayer.remove();
      geoLayer = L.geoJSON({{ type: 'FeatureCollection', features: filteredFeatures() }}, {{
        style: styleFeature,
        onEachFeature
      }}).addTo(map);
      selectedLayer = null;
      const bounds = geoLayer.getBounds();
      if (bounds.isValid()) map.fitBounds(bounds.pad(0.04), {{ animate: false }});
      updateSidebar();
      updateLegend();
    }}

    function updateSidebar() {{
      const list = filteredFeatures();
      const sorted = [...list].sort((a, b) => Number(b.properties[activeMetric] || 0) - Number(a.properties[activeMetric] || 0));
      const vals = valuesFor(activeMetric, list).sort((a, b) => a - b);
      const median = vals.length ? vals[Math.floor(vals.length / 2)] : 0;
      const assets = list.reduce((sum, feature) => sum + Number(feature.properties.climate_asset_sample_count || 0), 0);
      document.getElementById('townCount').textContent = list.length.toLocaleString();
      document.getElementById('topTown').textContent = sorted[0] ? sorted[0].properties.town : '-';
      document.getElementById('medianScore').textContent = format(median);
      document.getElementById('assetCount').textContent = assets.toLocaleString();

      const townList = document.getElementById('townList');
      townList.innerHTML = sorted.slice(0, 12).map((feature, index) => {{
        const p = feature.properties;
        const drivers = Array.isArray(p.key_drivers) ? p.key_drivers.slice(0, 3).join(', ') : p.key_drivers;
        return `<div class="town-row" data-geoid="${{p.geoid}}">
          <div class="town-main"><span>${{index + 1}}. ${{p.town}}</span><span>${{format(p[activeMetric])}}</span></div>
          <div class="town-sub">${{p.county}} County · ${{drivers || ''}}</div>
        </div>`;
      }}).join('');
      for (const row of townList.querySelectorAll('.town-row')) {{
        row.addEventListener('click', () => {{
          const geoid = row.getAttribute('data-geoid');
          geoLayer.eachLayer((layer) => {{
            if (layer.feature.properties.geoid === geoid) {{
              map.fitBounds(layer.getBounds().pad(0.8));
              layer.openPopup();
              layer.fire('click');
            }}
          }});
        }});
      }}
    }}

    function updateLegend() {{
      const b = breaks(activeMetric);
      const labels = [
        `≤ ${{format(b[0])}}`,
        `${{format(b[0])}} - ${{format(b[1])}}`,
        `${{format(b[1])}} - ${{format(b[2])}}`,
        `${{format(b[2])}} - ${{format(b[3])}}`,
        `${{format(b[3])}} - ${{format(b[4])}}`,
        `> ${{format(b[4])}}`
      ];
      document.getElementById('legend').innerHTML = `
        <div class="legend-title">${{METRICS[activeMetric]}}</div>
        ${{COLORS.map((color, index) => `<div class="legend-row"><span class="swatch" style="background:${{color}}"></span><span>${{labels[index]}}</span></div>`).join('')}}
      `;
    }}

    function populateCounties() {{
      const counties = ['All counties', ...Array.from(new Set(features.map((feature) => feature.properties.county))).sort()];
      const select = document.getElementById('countySelect');
      select.innerHTML = counties.map((county) => `<option value="${{county}}">${{county}}</option>`).join('');
    }}

    populateCounties();
    document.getElementById('metricSelect').addEventListener('change', (event) => {{
      activeMetric = event.target.value;
      drawMap();
    }});
    document.getElementById('countySelect').addEventListener('change', (event) => {{
      activeCounty = event.target.value;
      drawMap();
    }});
    document.getElementById('searchBox').addEventListener('input', (event) => {{
      searchText = event.target.value.trim().toLowerCase();
      drawMap();
    }});
    drawMap();
  </script>
</body>
</html>
"""


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
