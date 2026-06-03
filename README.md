# Transit Accessibility and Spatial Equity Analysis

Portfolio-quality GIS/data engineering project for Greater Portland, Maine.

The workflow combines public spatial data, Python ETL, PostgreSQL/PostGIS, spatial SQL analysis, QGIS/PyQGIS map automation, and automated reporting.

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
5. Run the spatial analysis SQL.
6. Write a markdown executive summary to `reports/executive_summary.md`.

To build the portfolio report after the pipeline has run:

```powershell
python python\build_report.py --config configs\project.toml --pdf
```

To build the interactive mobility dashboard:

```powershell
python python\build_dashboard.py --config configs\project.toml
```

Report outputs:

- `reports/transit_accessibility_report.html`
- `reports/transit_accessibility_report.pdf`
- `reports/mobility_insecurity_dashboard.html`
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

## Interactive Dashboard

`python/build_dashboard.py` exports a standalone browser dashboard with MapLibre GL JS, deck.gl, and Apache ECharts. It includes an interactive accessibility map, town and analysis-unit filters, KPI cards, all-town charts, tooltips, and a full KPI table.

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
