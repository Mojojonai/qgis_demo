# Transit Accessibility and Spatial Equity Analysis

Portfolio-quality GIS/data engineering project for Greater Portland and statewide Maine town screening.

The workflow combines public spatial data, statewide ACS demographics, Python ETL, PostgreSQL/PostGIS, spatial SQL analysis, QGIS/PyQGIS map automation, and automated reporting.

## Architecture

Open data sources -> Python ETL -> PostgreSQL/PostGIS -> spatial SQL -> QGIS visualization -> PDF/PNG outputs.

## Current Local Stack

- QGIS: `C:\Program Files\QGIS 3.44.11\bin\qgis-ltr-bin.exe`
- PostgreSQL: 17.10
- PostGIS: 3.6
- Database: `transit_accessibility`
- Host/port: `localhost:5764`
- User/password: `postgres/admin`
- pgAdmin: `C:\Program Files\PostgreSQL\17\pgAdmin 4\runtime\pgAdmin4.exe`

See [docs/local_setup.md](docs/local_setup.md) for connection details.

## Data Sources

The first build uses live public ArcGIS REST sources where available:

- Transit stops: GPCOG Greater Portland Transit Stop Inventory.
- Transit routes: GPCOG Greater Portland Transit Routes.
- Sidewalks: GPCOG/PACTS Region Sidewalks.
- Study area: GPCOG/PACTS Study Area.
- Demographics: U.S. Census Bureau ACS 2024 5-year table-based Summary File county subdivisions for Maine.

For layers not yet found in the GPCOG open data catalog, the ETL creates clearly marked synthetic sample records so the full PostGIS analysis and QGIS workflow can run end-to-end. Those layers are neighborhoods, schools, and hospitals.

## Run The First Pipeline

From the project root:

```powershell
python python\run_pipeline.py --config configs\project.toml
```

This will:

1. Enable PostGIS extensions.
2. Create the project schema.
3. Download/load available ArcGIS layers.
4. Generate synthetic fallback layers.
5. Load ACS town demographic indicators.
6. Run the spatial analysis SQL.
7. Write a markdown executive summary to `reports/executive_summary.md`.

To build the portfolio report after the pipeline has run:

```powershell
python python\build_report.py --config configs\project.toml --pdf
```

To build the interactive mobility dashboard:

```powershell
python python\build_dashboard.py --config configs\project.toml
```

To build the future livability and investment report suite:

```powershell
python python\build_future_reports.py --config configs\project.toml --pdf
```

To build the same-day climate-safe housing growth MVP:

```powershell
python python\build_climate_housing_mvp.py --config configs\project.toml --pdf
```

To load the first live climate-housing infrastructure/exposure layers:

```powershell
python python\load_climate_open_data.py --config configs\project.toml
```

To load Maine town boundaries and export a map-ready climate-housing GeoJSON:

```powershell
python python\load_maine_town_boundaries.py --config configs\project.toml
```

To build the standalone interactive climate-safe housing map:

```powershell
python python\build_climate_housing_map.py --config configs\project.toml
```

To build the climate-safe housing policy decision matrix:

```powershell
python python\build_climate_policy_matrix.py --config configs\project.toml --pdf
```

To build the synchronized climate-safe housing intelligence app:

```powershell
python python\build_climate_housing_app.py --config configs\project.toml
```

Report outputs:

- `reports/transit_accessibility_report.html`
- `reports/transit_accessibility_report.pdf`
- `reports/mobility_insecurity_dashboard.html`
- `reports/future_livability_investment_report.html`
- `reports/future_livability_investment_report.pdf`
- `reports/future_livability_investment_report.md`
- `reports/visionary_realtor_investor_brief.md`
- `reports/town_future_scorecards.md`
- `reports/town_missing_needs_matrix.md`
- `reports/maine_statewide_livability_investment_report.html`
- `reports/maine_statewide_livability_investment_report.pdf`
- `reports/maine_statewide_livability_investment_report.md`
- `reports/maine_government_priority_kpi_report.html`
- `reports/maine_government_priority_kpi_report.pdf`
- `reports/maine_government_priority_kpi_report.md`
- `reports/maine_government_priority_kpi_rankings.csv`
- `reports/climate_safe_housing_mvp_report.html`
- `reports/climate_safe_housing_mvp_report.pdf`
- `reports/climate_safe_housing_mvp_report.md`
- `reports/climate_safe_housing_town_screening.csv`
- `reports/climate_safe_housing_town_screening.geojson`
- `reports/climate_safe_housing_interactive_map.html`
- `reports/climate_housing_policy_decision_matrix.html`
- `reports/climate_housing_policy_decision_matrix.pdf`
- `reports/climate_housing_policy_decision_matrix.md`
- `reports/climate_housing_policy_decision_matrix.csv`
- `reports/climate_housing_intelligence_app.html`
- `reports/climate_housing_data_ingestion_summary.md`
- `reports/climate_housing_town_boundary_summary.md`
- `reports/maine_focus_town_comparison.md`
- `reports/maine_statewide_missing_needs_matrix.md`
- `reports/maine_statewide_town_rankings.csv`
- `reports/transit_accessibility_map.pdf`
- `reports/transit_accessibility_map.png`

## SQL Analysis

The SQL in `sql/02_analysis.sql` implements:

- 400-meter and 800-meter transit stop buffers.
- Population coverage estimates.
- Nearest transit stop distance by neighborhood.
- Sidewalk, school, and hospital access measures.
- Weighted accessibility score from 0 to 100.
- Underserved area ranking.
- Report-ready KPI tables for all towns and all analysis units.
- ACS-backed Mobility Need Index using accessibility gap, zero-car households, poverty, age 65+, and disability.

## Interactive Dashboard

`python/build_dashboard.py` exports a standalone browser dashboard with MapLibre GL JS, deck.gl, and Apache ECharts. It includes an interactive Mobility Need Index map, town and analysis-unit filters, KPI cards, all-town charts, tooltips, and a full KPI table.

## Future Livability And Investment Reports

`python/build_future_reports.py` builds a screening report suite for future living, real-estate, infrastructure, and local-service opportunity questions. It ranks towns by future livability and investor opportunity, then summarizes the missing needs that matter for housing, mobility, healthcare, aging, disability access, and workforce-support planning.

The Greater Portland report keeps the detailed accessibility metrics from the PostGIS/QGIS prototype. The statewide Maine report uses ACS county-subdivision indicators for every populated Maine town and city, including focus places such as Kennebunk, Brunswick, Hollis, Cumberland, Portland, South Portland, Westbrook, Falmouth, Scarborough, and Gorham.

The government KPI report adds statewide screens for housing pressure, transportation equity, aging in place, digital equity, workforce-support infrastructure, health access pressure, food/basic-needs pressure, child/family service demand, and climate-smart mobility opportunity. See [docs/government_kpi_framework.md](docs/government_kpi_framework.md) for KPI definitions.

The climate-safe housing growth proposal in [docs/climate_safe_housing_growth_areas_proposal.md](docs/climate_safe_housing_growth_areas_proposal.md) defines the next Maine-focused research project: flood risk, sea-level rise, infrastructure capacity, environmental constraints, housing need, and social vulnerability combined into a suitability and resilience-priority workflow.

`python/build_climate_housing_mvp.py` creates the first same-day implementation of that project. It ranks Maine towns from the statewide ACS indicators already in PostGIS, writes `climate_housing_town_screening`, and generates MVP report/CSV outputs. The full parcel-level claim of climate-safe suitability is intentionally deferred until FEMA NFHL, Maine Geological Survey sea-level-rise/storm-surge, wetlands, conservation, DEM, roads, bridges, culverts, parcels, and zoning overlays are ingested.

`python/load_climate_open_data.py` starts that ingestion by loading MaineDOT bridges, MaineDOT cross culverts, and Maine DEP sea-level-rise/flood impacted regulated-site layers into `climate_housing_infrastructure_assets`.

`python/load_maine_town_boundaries.py` downloads official Census TIGER/Line Maine county-subdivision boundaries, loads them into `climate_housing_town_boundaries`, and exports `reports/climate_safe_housing_town_screening.geojson` for QGIS or web mapping.

`python/build_climate_housing_map.py` creates a dependency-free standalone HTML/SVG map from the town screening GeoJSON with metric switching, county filtering, town search, town detail panels, and ranked town lists.

`python/build_climate_policy_matrix.py` converts the town-level screen into action categories for policymakers: near-term housing search, resilience before or alongside growth, seasonal market stabilization, infrastructure capacity build-out, hazard-overlay-first review, and statewide monitoring.

`python/build_climate_housing_app.py` builds a synchronized standalone dashboard app where KPI filters, policy-action categories, town search, map selection, profile details, action charts, scatter plots, and ranked tables all update together.

## QGIS Automation

The PyQGIS starter script is in `qgis/build_project.py`. It loads the PostGIS layers, applies basic symbology, builds a print layout, and exports map outputs. Run it from the QGIS Python environment after the database pipeline succeeds.

## Project Structure

```text
configs/      Local project configuration
data/         Raw and processed data outputs
docs/         Setup and data-source notes
notebooks/    Optional ML and exploratory notebooks
python/       ETL, reporting, and orchestration scripts
qgis/         PyQGIS automation and generated QGIS projects
reports/      Generated summaries and map exports
sql/          PostGIS schema and analysis SQL
```
