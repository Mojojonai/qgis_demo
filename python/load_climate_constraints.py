from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from psycopg2.extras import Json

from config import ensure_directories, load_config, resolve_path
from db import connect, run_sql_file


MAINE_BBOX = "-71.2,42.9,-66.8,47.5"


@dataclass(frozen=True)
class ConstraintSource:
    key: str
    url: str
    table: str
    source_name: str
    kind: str
    type_value: str
    where: str = "1=1"
    scenario: str = ""
    class_fields: tuple[str, ...] = ()
    regulatory_fields: tuple[str, ...] = ()
    out_fields: str = "*"
    timeout_seconds: int | None = None
    retries: int = 5


SOURCES = [
    ConstraintSource(
        key="fema_nfhl_flood_hazard_zones",
        url="https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28",
        table="climate_housing_hazard_zones",
        source_name="FEMA National Flood Hazard Layer",
        kind="hazard",
        type_value="flood",
        where="SFHA_TF='T' OR ZONE_SUBTY='0.2 PCT ANNUAL CHANCE FLOOD HAZARD'",
        scenario="effective NFHL special and 0.2 percent annual chance flood hazard",
        class_fields=("FLD_ZONE", "ZONE_SUBTY"),
        regulatory_fields=("SFHA_TF",),
    ),
    ConstraintSource(
        key="maine_conserved_lands",
        url="https://services5.arcgis.com/8TufBwUCMF4Azg37/arcgis/rest/services/Maine_Conserved_Lands/FeatureServer/16",
        table="climate_housing_environmental_constraints",
        source_name="Maine GeoLibrary Conserved Lands",
        kind="environment",
        type_value="conserved_land",
        class_fields=("DESIGNATION", "CONS1_TYPE", "PURPOSE1"),
        regulatory_fields=("GAP_STATUS", "PUB_ACCESS"),
    ),
    ConstraintSource(
        key="nwi_wetlands",
        url="https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/Wetlands/MapServer/0",
        table="climate_housing_environmental_constraints",
        source_name="U.S. Fish and Wildlife Service National Wetlands Inventory",
        kind="environment",
        type_value="wetland",
        class_fields=("WETLAND_TYPE", "ATTRIBUTE", "CLASS_NAME"),
        regulatory_fields=("SYSTEM_NAME", "WATER_REGIME_NAME"),
        out_fields="Wetlands.OBJECTID,Wetlands.ATTRIBUTE,Wetlands.WETLAND_TYPE,Wetlands.ACRES",
        timeout_seconds=20,
        retries=2,
    ),
]


def request_json(url: str, timeout: int = 120, retries: int = 5) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "MaineClimateSafeHousingProject/1.0"})
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("error"):
                raise RuntimeError(f"ArcGIS service error for {url}: {payload['error']}")
            return payload
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == retries - 1:
                raise
        except (TimeoutError, URLError):
            if attempt == retries - 1:
                raise
        time.sleep(min(12, 2 ** attempt))
    raise RuntimeError(f"Unable to retrieve {url}")


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


def fetch_arcgis_geojson(
    source: ConstraintSource,
    page_size: int,
    timeout: int,
    max_features: int | None = None,
) -> dict[str, Any]:
    source_timeout = source.timeout_seconds or timeout
    metadata = request_json(metadata_url(source.url), timeout=source_timeout, retries=source.retries)
    oid_field = get_oid_field(metadata)
    service_limit = int(metadata.get("maxRecordCount") or page_size)
    effective_page_size = min(page_size, service_limit)
    features: list[dict[str, Any]] = []
    offset = 0

    while True:
        remaining = None if max_features is None else max_features - len(features)
        if remaining is not None and remaining <= 0:
            break
        batch_size = min(effective_page_size, remaining) if remaining is not None else effective_page_size
        params: dict[str, Any] = {
            "where": source.where,
            "geometry": MAINE_BBOX,
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": source.out_fields,
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": batch_size,
        }
        if oid_field:
            params["orderByFields"] = oid_field
        payload = request_json(
            arcgis_query_url(source.url, params),
            timeout=source_timeout,
            retries=source.retries,
        )
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
            "maine_bbox": MAINE_BBOX,
            "where": source.where,
            "feature_count": len(features),
            "feature_cap": max_features,
        },
        "features": features,
    }


def get_any(props: dict[str, Any], fields: tuple[str, ...]) -> Any:
    lower = {str(key).lower(): value for key, value in props.items()}
    for field in fields:
        field_lower = field.lower()
        for key, value in lower.items():
            if (key == field_lower or key.endswith(f".{field_lower}")) and value not in (None, ""):
                return value
    return None


def combine_fields(props: dict[str, Any], fields: tuple[str, ...]) -> str | None:
    values: list[str] = []
    for field in fields:
        value = get_any(props, (field,))
        if value not in (None, "") and str(value) not in values:
            values.append(str(value))
    return " | ".join(values) if values else None


def geom_json(feature: dict[str, Any]) -> str:
    return json.dumps(feature["geometry"])


def load_hazards(conn, source: ConstraintSource, features: list[dict[str, Any]]) -> int:
    sql = """
        INSERT INTO climate_housing_hazard_zones (
            source_name,
            hazard_type,
            scenario,
            hazard_class,
            source_url,
            raw_properties,
            geom
        )
        SELECT
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            cleaned.geom
        FROM (
            SELECT ST_Multi(
                ST_CollectionExtract(
                    ST_MakeValid(ST_Force2D(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))),
                    3
                )
            ) AS geom
        ) cleaned
        WHERE NOT ST_IsEmpty(cleaned.geom)
    """
    rows = []
    for feature in features:
        props = feature.get("properties", {})
        rows.append((
            source.source_name,
            source.type_value,
            source.scenario,
            combine_fields(props, source.class_fields),
            source.url,
            Json({**props, "_source_key": source.key, "_regulatory_status": combine_fields(props, source.regulatory_fields)}),
            geom_json(feature),
        ))
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    return len(rows)


def load_environmental_constraints(conn, source: ConstraintSource, features: list[dict[str, Any]]) -> int:
    sql = """
        INSERT INTO climate_housing_environmental_constraints (
            source_name,
            constraint_type,
            constraint_class,
            regulatory_status,
            source_url,
            raw_properties,
            geom
        )
        SELECT
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            cleaned.geom
        FROM (
            SELECT ST_Multi(
                ST_CollectionExtract(
                    ST_MakeValid(ST_Force2D(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))),
                    3
                )
            ) AS geom
        ) cleaned
        WHERE NOT ST_IsEmpty(cleaned.geom)
    """
    rows = []
    for feature in features:
        props = feature.get("properties", {})
        rows.append((
            source.source_name,
            source.type_value,
            combine_fields(props, source.class_fields),
            combine_fields(props, source.regulatory_fields),
            source.url,
            Json({**props, "_source_key": source.key}),
            geom_json(feature),
        ))
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    return len(rows)


def clear_loaded_sources(conn) -> None:
    hazard_sources = [source.source_name for source in SOURCES if source.kind == "hazard"]
    environment_sources = [source.source_name for source in SOURCES if source.kind == "environment"]
    with conn.cursor() as cur:
        cur.execute("DELETE FROM climate_housing_hazard_zones WHERE source_name = ANY(%s)", (hazard_sources,))
        cur.execute(
            "DELETE FROM climate_housing_environmental_constraints WHERE source_name = ANY(%s)",
            (environment_sources,),
        )


def save_raw(cfg: dict[str, Any], source: ConstraintSource, payload: dict[str, Any]) -> Path:
    path = resolve_path(cfg, "raw_dir") / f"{source.key}.geojson"
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    return path


def write_summary(
    cfg: dict[str, Any],
    counts: dict[str, int],
    errors: dict[str, str],
    max_features: int | None,
) -> Path:
    path = resolve_path(cfg, "reports_dir") / "climate_housing_constraint_ingestion_summary.md"
    lines = [
        "# Climate Housing Constraint Ingestion Summary",
        "",
        "This audit records authoritative polygon overlays clipped to the Maine bounding box and loaded into PostGIS.",
        "",
        f"Feature cap per source: **{max_features if max_features is not None else 'none - full source load'}**.",
        "",
        "| Source | Model Role | Filter | Features Loaded | URL |",
        "| --- | --- | --- | --- | --- |",
    ]
    for source in SOURCES:
        role = f"{source.kind}: {source.type_value}"
        lines.append(
            f"| {source.source_name} | {role} | `{source.where}` | {counts.get(source.key, 0)} | {source.url} |"
        )
    lines.extend([
        "",
        "## Source Errors",
        "",
    ])
    if errors:
        lines.extend(f"- **{key}:** {message}" for key, message in errors.items())
    else:
        lines.append("- None.")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- FEMA polygons include Special Flood Hazard Areas and mapped 0.2 percent annual-chance flood hazard areas.",
        "- Conserved land and NWI wetland polygons are treated as environmental screening constraints, not automatic legal determinations.",
        "- The candidate-grid model measures polygon overlap as a share of each grid/town intersection.",
        "- A feature cap makes this a bounded reproducible screening run. Remove `--max-features` for complete source ingestion when runtime and storage allow.",
        "- Parcel boundaries, local zoning, shoreland zoning, municipal water/wastewater capacity, and DEM-derived slope remain required before site selection or permitting decisions.",
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
    errors: dict[str, str] = {}

    with connect(cfg) as conn:
        clear_loaded_sources(conn)
    for source in SOURCES:
        try:
            print(f"Fetching {source.key}...")
            payload = fetch_arcgis_geojson(source, page_size=page_size, timeout=timeout, max_features=max_features)
            save_raw(cfg, source, payload)
            features = payload.get("features", [])
            with connect(cfg) as conn:
                if source.kind == "hazard":
                    counts[source.key] = load_hazards(conn, source, features)
                else:
                    counts[source.key] = load_environmental_constraints(conn, source, features)
        except Exception as exc:
            counts[source.key] = 0
            errors[source.key] = f"{type(exc).__name__}: {exc}"
            print(f"Warning: {source.key} could not be loaded: {exc}")

    summary_path = write_summary(cfg, counts, errors=errors, max_features=max_features)
    return counts, summary_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Load FEMA flood, wetlands, and conserved-land polygons for Maine.")
    parser.add_argument("--config", default="configs/project.toml")
    parser.add_argument("--max-features", type=int, default=None, help="Optional per-source cap for bounded runs.")
    args = parser.parse_args()
    counts, summary_path = run_load(args.config, max_features=args.max_features)
    for key, count in counts.items():
        print(f"{key}: {count}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
