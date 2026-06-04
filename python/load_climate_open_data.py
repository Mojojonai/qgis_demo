from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from psycopg2.extras import Json

from config import ensure_directories, load_config, resolve_path
from db import connect, run_sql_file


@dataclass(frozen=True)
class ClimateSource:
    key: str
    url: str
    table: str
    source_name: str
    category: str
    asset_type: str = ""
    hazard_type: str = ""
    scenario: str = ""
    hazard_class: str = ""
    name_fields: tuple[str, ...] = ()
    condition_fields: tuple[str, ...] = ()


MAINE_DOT_BASE = "https://gis.maine.gov/mapservices/rest/services/dot/MaineDOT_OpenData/MapServer"
MAINE_DEP_SLR_BASE = "https://gis.maine.gov/mapservices/rest/services/dep/MaineDEPSeaLevelRiseStudy/MapServer"


def dep_impacted_site_sources(scenario: str, hazard_type: str, layer_ids: dict[str, int]) -> list[ClimateSource]:
    return [
        ClimateSource(
            key=f"dep_{scenario.replace('.', '_').replace('-', '_')}_{facility_key}",
            url=f"{MAINE_DEP_SLR_BASE}/{layer_id}",
            table="climate_housing_infrastructure_assets",
            source_name="Maine DEP Sea Level Rise Study",
            category="infrastructure",
            asset_type=f"{facility_key}_exposed_to_{scenario}",
            hazard_type=hazard_type,
            scenario=scenario,
            hazard_class="potentially impacted regulated site",
            name_fields=("FACILITY", "facility", "SITE_NAME", "site_name", "name", "NAME"),
        )
        for facility_key, layer_id in layer_ids.items()
    ]


SOURCES = [
    ClimateSource(
        key="mainedot_bridges",
        url=f"{MAINE_DOT_BASE}/0",
        table="climate_housing_infrastructure_assets",
        source_name="MaineDOT OpenData - Bridges",
        category="infrastructure",
        asset_type="bridge",
        name_fields=("brdg_name", "BRDG_NAME", "facility", "FACILITY"),
        condition_fields=("suff_rate", "dkrating_desc", "suprating_desc", "subrating_desc", "culvrating_desc", "scourcrit_desc"),
    ),
    ClimateSource(
        key="mainedot_cross_culverts",
        url=f"{MAINE_DOT_BASE}/54",
        table="climate_housing_infrastructure_assets",
        source_name="MaineDOT OpenData - Cross Culverts",
        category="infrastructure",
        asset_type="cross_culvert",
        name_fields=("culv_id", "culvert_id", "road_name", "strtname", "route_name"),
        condition_fields=("condition", "cond_desc", "culvrating_desc", "scourcrit_desc"),
    ),
    *dep_impacted_site_sources("1.6ft_slr", "sea_level_rise", {
        "fuel_storage_tank": 1,
        "mepdes_facility": 2,
        "remediation_site": 3,
        "closed_municipal_landfill": 4,
    }),
    *dep_impacted_site_sources("3.9ft_slr", "sea_level_rise", {
        "fuel_storage_tank": 6,
        "mepdes_facility": 7,
        "remediation_site": 8,
        "closed_municipal_landfill": 9,
    }),
    *dep_impacted_site_sources("8.8ft_slr", "sea_level_rise", {
        "fuel_storage_tank": 11,
        "mepdes_facility": 12,
        "remediation_site": 13,
        "closed_municipal_landfill": 14,
    }),
    *dep_impacted_site_sources("100yr_flood", "flood", {
        "fuel_storage_tank": 21,
        "mepdes_facility": 22,
        "remediation_site": 23,
        "closed_municipal_landfill": 24,
    }),
    *dep_impacted_site_sources("500yr_flood", "flood", {
        "fuel_storage_tank": 16,
        "mepdes_facility": 17,
        "remediation_site": 18,
        "closed_municipal_landfill": 19,
    }),
]


def request_json(url: str, timeout: int = 120) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "TransitAccessibilityProject/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def arcgis_query_url(layer_url: str, params: dict[str, Any]) -> str:
    return f"{layer_url.rstrip('/')}/query?{urlencode(params)}"


def metadata_url(layer_url: str) -> str:
    return f"{layer_url.rstrip('/')}?{urlencode({'f': 'json'})}"


def get_oid_field(metadata: dict[str, Any]) -> str | None:
    oid = metadata.get("objectIdField")
    if oid:
        return oid
    for field in metadata.get("fields") or []:
        if field.get("type") == "esriFieldTypeOID":
            return field.get("name")
    return None


def fetch_arcgis_geojson(source: ClimateSource, page_size: int, timeout: int, max_features: int | None = None) -> dict[str, Any]:
    metadata = request_json(metadata_url(source.url), timeout=timeout)
    oid_field = get_oid_field(metadata)
    features: list[dict[str, Any]] = []
    offset = 0
    while True:
        remaining = None if max_features is None else max_features - len(features)
        if remaining is not None and remaining <= 0:
            break
        batch_size = min(page_size, remaining) if remaining is not None else page_size
        params: dict[str, Any] = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": batch_size,
        }
        if oid_field:
            params["orderByFields"] = oid_field
        payload = request_json(arcgis_query_url(source.url, params), timeout=timeout)
        batch = [feature for feature in payload.get("features", []) if feature.get("geometry")]
        features.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
        time.sleep(0.15)
    return {
        "type": "FeatureCollection",
        "metadata": {
            "source_key": source.key,
            "source_name": source.source_name,
            "source_url": source.url,
            "feature_count": len(features),
            "feature_cap": max_features,
        },
        "features": features,
    }


def get_any(props: dict[str, Any], fields: tuple[str, ...]) -> Any:
    lower = {str(key).lower(): value for key, value in props.items()}
    for field in fields:
        if field in props and props[field] not in (None, ""):
            return props[field]
        value = lower.get(field.lower())
        if value not in (None, ""):
            return value
    return None


def geom_json(feature: dict[str, Any]) -> str:
    return json.dumps(feature["geometry"])


def load_infrastructure(conn, source: ClimateSource, features: list[dict[str, Any]]) -> int:
    sql = """
        INSERT INTO climate_housing_infrastructure_assets (
            source_name,
            asset_type,
            asset_name,
            owner,
            condition_rating,
            source_url,
            raw_properties,
            geom
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)
        )
    """
    rows = []
    for feature in features:
        props = feature.get("properties", {})
        enriched = {
            **props,
            "_source_key": source.key,
            "_hazard_type": source.hazard_type,
            "_scenario": source.scenario,
            "_hazard_class": source.hazard_class,
        }
        rows.append((
            source.source_name,
            source.asset_type,
            get_any(props, source.name_fields),
            get_any(props, ("owner", "OWNER", "owner_desc", "OWNER_DESC")),
            get_any(props, source.condition_fields),
            source.url,
            Json(enriched),
            geom_json(feature),
        ))
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    return len(rows)


def clear_loaded_sources(conn) -> None:
    source_names = sorted({source.source_name for source in SOURCES})
    asset_types = sorted({source.asset_type for source in SOURCES if source.asset_type})
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM climate_housing_infrastructure_assets
            WHERE source_name = ANY(%s)
               OR asset_type = ANY(%s);
            """,
            (source_names, asset_types),
        )


def save_raw(cfg: dict[str, Any], source: ClimateSource, payload: dict[str, Any]) -> Path:
    path = resolve_path(cfg, "raw_dir") / f"{source.key}.geojson"
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    return path


def write_summary(cfg: dict[str, Any], counts: dict[str, int], max_features: int | None) -> Path:
    reports_dir = resolve_path(cfg, "reports_dir")
    path = reports_dir / "climate_housing_data_ingestion_summary.md"
    rows = [
        [source.key, source.source_name, source.asset_type, source.scenario or "", counts.get(source.key, 0), source.url]
        for source in SOURCES
    ]
    lines = [
        "# Climate Housing Data Ingestion Summary",
        "",
        "This summary records the first live spatial layers ingested for the climate-safe housing workflow.",
        "",
        f"Feature cap per source: **{max_features if max_features is not None else 'none - full source load'}**.",
        "",
        "| Source Key | Source | Asset Type | Scenario | Features Loaded | URL |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    lines.extend("| " + " | ".join(str(item) for item in row) + " |" for row in rows)
    lines.extend([
        "",
        "## Current Status",
        "",
        "- Loaded MaineDOT bridges and cross culverts as infrastructure assets.",
        "- Loaded Maine DEP regulated-site exposure layers for 1.6 ft, 3.9 ft, and 8.8 ft sea-level-rise scenarios plus 100-year and 500-year flood exposure groups where the service provides queryable features.",
        "- This run is a smoke-test/sample run when a feature cap is shown above. Re-run without `--max-features` for the full source load.",
        "- FEMA NFHL polygon overlays, Maine Geological Survey inundation polygons, NWI wetlands, conservation lands, DEM slope/elevation, parcels, and zoning are still the next ingestion targets.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_load(config_path: str = "configs/project.toml", max_features: int | None = None) -> tuple[dict[str, int], Path]:
    cfg = load_config(config_path)
    ensure_directories(cfg)
    run_sql_file(cfg, "sql/03_climate_housing_schema.sql")
    page_size = int(cfg.get("arcgis", {}).get("page_size", 2000))
    timeout = int(cfg.get("arcgis", {}).get("timeout_seconds", 120))
    counts: dict[str, int] = {}
    with connect(cfg) as conn:
        clear_loaded_sources(conn)
        for source in SOURCES:
            payload = fetch_arcgis_geojson(source, page_size=page_size, timeout=timeout, max_features=max_features)
            save_raw(cfg, source, payload)
            features = payload.get("features", [])
            counts[source.key] = load_infrastructure(conn, source, features)
    summary_path = write_summary(cfg, counts, max_features=max_features)
    return counts, summary_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Load live open data layers for the Maine climate-safe housing workflow.")
    parser.add_argument("--config", default="configs/project.toml")
    parser.add_argument("--max-features", type=int, default=None, help="Optional per-source feature cap for smoke testing.")
    args = parser.parse_args()
    counts, summary_path = run_load(args.config, max_features=args.max_features)
    for key, count in counts.items():
        print(f"{key}: {count}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
