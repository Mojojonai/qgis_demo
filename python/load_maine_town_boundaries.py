from __future__ import annotations

import argparse
import time
import json
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

from config import ensure_directories, load_config, resolve_path
from db import connect, run_sql_file


TIGER_2024_MAINE_COUSUB_URL = "https://www2.census.gov/geo/tiger/TIGER2024/COUSUB/tl_2024_23_cousub.zip"

MAINE_COUNTIES = {
    "001": "Androscoggin",
    "003": "Aroostook",
    "005": "Cumberland",
    "007": "Franklin",
    "009": "Hancock",
    "011": "Kennebec",
    "013": "Knox",
    "015": "Lincoln",
    "017": "Oxford",
    "019": "Penobscot",
    "021": "Piscataquis",
    "023": "Sagadahoc",
    "025": "Somerset",
    "027": "Waldo",
    "029": "Washington",
    "031": "York",
}


def download_source(raw_dir: Path, force: bool = False) -> Path:
    path = raw_dir / "tl_2024_23_cousub.zip"
    if path.exists() and not force:
        return path
    tmp_path = path.with_suffix(".zip.tmp")
    last_error: Exception | None = None
    for attempt in range(1, 5):
        try:
            request = Request(TIGER_2024_MAINE_COUSUB_URL, headers={"User-Agent": "TransitAccessibilityProject/1.0"})
            with urlopen(request, timeout=300) as response, tmp_path.open("wb") as fh:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    fh.write(chunk)
            tmp_path.replace(path)
            return path
        except Exception as exc:
            last_error = exc
            if tmp_path.exists():
                tmp_path.unlink()
            time.sleep(attempt)
    raise RuntimeError(f"Failed to download {TIGER_2024_MAINE_COUSUB_URL}") from last_error


def ogr2ogr_path(cfg: dict) -> Path | str:
    qgis = cfg.get("qgis", {})
    prefix = qgis.get("prefix_path")
    if prefix:
        candidate = Path(prefix) / "bin" / "ogr2ogr.exe"
        if candidate.exists():
            return candidate
    return "ogr2ogr"


def pg_connection_string(cfg: dict) -> str:
    db = cfg["database"]
    return (
        f"PG:host={db['host']} "
        f"port={db['port']} "
        f"dbname={db['database']} "
        f"user={db['user']} "
        f"password={db['password']}"
    )


def county_case_sql() -> str:
    clauses = " ".join(f"WHEN '{fips}' THEN '{name}'" for fips, name in MAINE_COUNTIES.items())
    return f"CASE countyfp {clauses} ELSE countyfp END"


def load_raw_with_ogr(cfg: dict, zip_path: Path) -> None:
    raw_table = "climate_housing_town_boundaries_raw"
    with connect(cfg) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {raw_table};")
    vsi_path = f"/vsizip/{zip_path.as_posix()}"
    command = [
        str(ogr2ogr_path(cfg)),
        "-f",
        "PostgreSQL",
        pg_connection_string(cfg),
        vsi_path,
        "-nln",
        raw_table,
        "-overwrite",
        "-t_srs",
        "EPSG:4326",
        "-nlt",
        "MULTIPOLYGON",
        "-lco",
        "GEOMETRY_NAME=geom",
    ]
    subprocess.run(command, check=True)


def load_boundaries(cfg: dict, zip_path: Path) -> int:
    load_raw_with_ogr(cfg, zip_path)
    county_case = county_case_sql()
    sql = f"""
        DELETE FROM climate_housing_town_boundaries;

        INSERT INTO climate_housing_town_boundaries (
            geoid,
            state_fips,
            county_fips,
            county_subdivision_fips,
            town,
            name_lsad,
            county,
            land_area_sq_m,
            water_area_sq_m,
            source_name,
            source_url,
            raw_properties,
            geom
        )
        SELECT
            geoid,
            statefp,
            countyfp,
            cousubfp,
            name,
            namelsad,
            {county_case},
            aland::numeric,
            awater::numeric,
            'U.S. Census TIGER/Line 2024 County Subdivisions',
            %s,
            jsonb_build_object(
                'STATEFP', statefp,
                'COUNTYFP', countyfp,
                'COUSUBFP', cousubfp,
                'COUSUBNS', cousubns,
                'GEOID', geoid,
                'NAME', name,
                'NAMELSAD', namelsad,
                'LSAD', lsad,
                'CLASSFP', classfp,
                'MTFCC', mtfcc,
                'FUNCSTAT', funcstat,
                'ALAND', aland,
                'AWATER', awater,
                'INTPTLAT', intptlat,
                'INTPTLON', intptlon
            ),
            ST_Multi(ST_Force2D(geom))
        FROM climate_housing_town_boundaries_raw
        ON CONFLICT (geoid) DO UPDATE SET
            state_fips = EXCLUDED.state_fips,
            county_fips = EXCLUDED.county_fips,
            county_subdivision_fips = EXCLUDED.county_subdivision_fips,
            town = EXCLUDED.town,
            name_lsad = EXCLUDED.name_lsad,
            county = EXCLUDED.county,
            land_area_sq_m = EXCLUDED.land_area_sq_m,
            water_area_sq_m = EXCLUDED.water_area_sq_m,
            source_name = EXCLUDED.source_name,
            source_url = EXCLUDED.source_url,
            raw_properties = EXCLUDED.raw_properties,
            geom = EXCLUDED.geom;
    """
    with connect(cfg) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (TIGER_2024_MAINE_COUSUB_URL,))
            cur.execute("SELECT COUNT(*) FROM climate_housing_town_boundaries;")
            return int(cur.fetchone()[0])


def export_screening_geojson(cfg: dict) -> Path:
    reports_dir = resolve_path(cfg, "reports_dir")
    path = reports_dir / "climate_safe_housing_town_screening.geojson"
    query = """
        WITH asset_counts AS (
            SELECT
                b.geoid,
                COUNT(a.id) AS climate_asset_sample_count,
                COUNT(a.id) FILTER (WHERE a.asset_type = 'bridge') AS bridge_sample_count,
                COUNT(a.id) FILTER (WHERE a.asset_type = 'cross_culvert') AS culvert_sample_count,
                COUNT(a.id) FILTER (WHERE a.asset_type LIKE '%slr%') AS slr_site_sample_count,
                COUNT(a.id) FILTER (WHERE a.asset_type LIKE '%flood%') AS flood_site_sample_count
            FROM climate_housing_town_boundaries b
            LEFT JOIN climate_housing_infrastructure_assets a
                ON ST_Intersects(b.geom, a.geom)
            GROUP BY b.geoid
        )
        SELECT
            b.geoid,
            a.town,
            b.town AS boundary_town,
            b.name_lsad AS boundary_name,
            b.county,
            b.land_area_sq_m,
            b.water_area_sq_m,
            s.acs_population,
            s.climate_safe_housing_mvp_score,
            s.housing_need_score,
            s.social_vulnerability_score,
            s.infrastructure_efficiency_proxy_score,
            s.resilience_investment_priority_score,
            s.mvp_priority_lane,
            s.hazard_overlay_status,
            s.key_drivers,
            COALESCE(c.climate_asset_sample_count, 0) AS climate_asset_sample_count,
            COALESCE(c.bridge_sample_count, 0) AS bridge_sample_count,
            COALESCE(c.culvert_sample_count, 0) AS culvert_sample_count,
            COALESCE(c.slr_site_sample_count, 0) AS slr_site_sample_count,
            COALESCE(c.flood_site_sample_count, 0) AS flood_site_sample_count,
            ST_AsGeoJSON(ST_SimplifyPreserveTopology(b.geom, 0.001)) AS geometry
        FROM climate_housing_town_boundaries b
        JOIN acs_town_demographics a
            ON a.state_fips = b.state_fips
           AND a.county_fips = b.county_fips
           AND a.county_subdivision_fips = b.county_subdivision_fips
        LEFT JOIN climate_housing_town_screening s
            ON lower(s.town) = lower(a.town)
           AND lower(s.county) = lower(b.county)
        LEFT JOIN asset_counts c
            ON c.geoid = b.geoid
        WHERE a.total_population > 0
          AND s.town IS NOT NULL
        ORDER BY s.climate_safe_housing_mvp_score DESC NULLS LAST;
    """
    features = []
    with connect(cfg) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [description.name for description in cur.description]
            for row in cur.fetchall():
                record = dict(zip(columns, row))
                geometry = json.loads(record.pop("geometry"))
                features.append({"type": "Feature", "properties": record, "geometry": geometry})
    feature_collection = {
        "type": "FeatureCollection",
        "metadata": {
            "title": "Climate-safe housing MVP town screening",
            "geometry_source": TIGER_2024_MAINE_COUSUB_URL,
            "geometry_simplification_degrees": 0.001,
            "hazard_overlay_status": "sample infrastructure/exposure assets only; FEMA/MGS/wetlands/conservation/DEM overlays pending",
            "feature_count": len(features),
        },
        "features": features,
    }
    path.write_text(json.dumps(feature_collection, separators=(",", ":"), default=str), encoding="utf-8")
    return path


def geojson_feature_count(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return int(payload.get("metadata", {}).get("feature_count") or len(payload.get("features", [])))


def write_summary(cfg: dict, boundary_count: int, geojson_path: Path, zip_path: Path) -> Path:
    reports_dir = resolve_path(cfg, "reports_dir")
    path = reports_dir / "climate_housing_town_boundary_summary.md"
    feature_count = geojson_feature_count(geojson_path)
    lines = [
        "# Climate Housing Town Boundary Summary",
        "",
        f"- Boundary source: U.S. Census TIGER/Line 2024 Maine county subdivisions.",
        f"- Source URL: `{TIGER_2024_MAINE_COUSUB_URL}`.",
        f"- Raw cache: `{zip_path}`.",
        f"- Boundaries loaded to PostGIS: **{boundary_count}**.",
        f"- Scored populated places exported to GeoJSON: **{feature_count}**.",
        f"- Map-ready screening GeoJSON: `{geojson_path}`.",
        "",
        "## What This Enables",
        "",
        "- QGIS can now map town-level climate-safe housing MVP scores as polygons.",
        "- Web maps can load `reports/climate_safe_housing_town_screening.geojson` directly.",
        "- Climate/infrastructure asset sample counts can be spatially joined to towns.",
        "- The next step is adding full hazard and constraint polygons, then calculating true exposure shares by town, tract, parcel, or grid cell.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_load(config_path: str = "configs/project.toml", force_download: bool = False) -> list[Path]:
    cfg = load_config(config_path)
    ensure_directories(cfg)
    run_sql_file(cfg, "sql/03_climate_housing_schema.sql")
    raw_dir = resolve_path(cfg, "raw_dir")
    zip_path = download_source(raw_dir, force=force_download)
    boundary_count = load_boundaries(cfg, zip_path)
    geojson_path = export_screening_geojson(cfg)
    summary_path = write_summary(cfg, boundary_count, geojson_path, zip_path)
    return [zip_path, geojson_path, summary_path]


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Maine Census town boundaries and export climate-housing MVP map GeoJSON.")
    parser.add_argument("--config", default="configs/project.toml")
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()
    for path in run_load(args.config, force_download=args.force_download):
        print(path)


if __name__ == "__main__":
    main()
