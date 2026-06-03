from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from psycopg2.extras import Json

from config import ensure_directories, load_config, resolve_path
from db import connect


BASE_TABLES = (
    "transit_stops",
    "transit_routes",
    "sidewalks",
    "study_area",
    "neighborhoods",
    "schools",
    "hospitals",
)


def setup_logging(cfg: dict[str, Any]) -> None:
    logs_dir = resolve_path(cfg, "logs_dir")
    logs_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(logs_dir / "etl.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def request_json(url: str, timeout: int) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": "TransitAccessibilityProject/1.0"})
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def arcgis_url(layer_url: str, suffix: str, params: dict[str, Any]) -> str:
    return f"{layer_url.rstrip('/')}/{suffix}?{urlencode(params)}"


def fetch_arcgis_geojson(source: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    layer_url = source["url"].rstrip("/")
    timeout = int(cfg["arcgis"].get("timeout_seconds", 60))
    page_size = int(cfg["arcgis"].get("page_size", 2000))
    metadata = request_json(f"{layer_url}?{urlencode({'f': 'json'})}", timeout)
    oid_field = metadata.get("objectIdField")
    if not oid_field:
        for field in metadata.get("fields", []):
            if field.get("type") == "esriFieldTypeOID":
                oid_field = field.get("name")
                break

    features: list[dict[str, Any]] = []
    offset = 0
    while True:
        params: dict[str, Any] = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": page_size,
        }
        if oid_field:
            params["orderByFields"] = oid_field
        url = arcgis_url(layer_url, "query", params)
        payload = request_json(url, timeout)
        batch = payload.get("features", [])
        features.extend(batch)
        logging.info("Fetched %s features from %s at offset %s", len(batch), source["key"], offset)
        if len(batch) < page_size:
            break
        offset += page_size
        time.sleep(0.2)

    return {"type": "FeatureCollection", "features": features}


def get_any(props: dict[str, Any], *keys: str) -> Any:
    lower = {str(k).lower(): v for k, v in props.items()}
    for key in keys:
        if key in props:
            return props[key]
        value = lower.get(key.lower())
        if value not in (None, ""):
            return value
    return None


def as_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


def geom_json(feature: dict[str, Any]) -> str:
    return json.dumps(feature["geometry"])


def load_transit_stops(conn, features: list[dict[str, Any]], synthetic: bool) -> None:
    sql = """
        INSERT INTO transit_stops (
            source_id, stop_code, stop_name, route_name, is_hub, is_on_demand,
            is_school_stop, is_wheelchair_accessible, is_synthetic, raw_properties, geom
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
    """
    rows = []
    for feature in features:
        props = feature.get("properties", {})
        rows.append((
            str(get_any(props, "GlobalID", "SDE_ID", "STOP_ID", "OBJECTID") or ""),
            get_any(props, "TRANSIT_STOP_CODE", "stop_code", "stop_id"),
            get_any(props, "STOP_LOCATION", "stop_name", "name") or f"Stop {get_any(props, 'stop_id', 'STOP_ID', 'FID') or ''}".strip(),
            get_any(props, "ROUTE_NAME", "route_name"),
            as_bool(get_any(props, "IS_HUB")),
            as_bool(get_any(props, "IS_ON_DEMAND")),
            as_bool(get_any(props, "IS_SCHOOL_STOP")),
            as_bool(get_any(props, "IS_WHEELCHAIR_ACCESS")),
            synthetic,
            Json(props),
            geom_json(feature),
        ))
    with conn.cursor() as cur:
        cur.executemany(sql, rows)


def load_transit_routes(conn, features: list[dict[str, Any]], synthetic: bool) -> None:
    sql = """
        INSERT INTO transit_routes (source_id, route_name, agency, is_synthetic, raw_properties, geom)
        VALUES (%s, %s, %s, %s, %s, ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)))
    """
    rows = []
    for feature in features:
        props = feature.get("properties", {})
        rows.append((
            str(get_any(props, "GlobalID", "SDE_ID", "MAP_ID", "OBJECTID") or ""),
            get_any(props, "ROUTE_NAME", "route_name", "name"),
            get_any(props, "agency", "AGENCY"),
            synthetic,
            Json(props),
            geom_json(feature),
        ))
    with conn.cursor() as cur:
        cur.executemany(sql, rows)


def load_sidewalks(conn, features: list[dict[str, Any]], synthetic: bool) -> None:
    sql = """
        INSERT INTO sidewalks (source_id, material, condition, width_ft, is_synthetic, raw_properties, geom)
        VALUES (%s, %s, %s, %s, %s, %s, ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)))
    """
    rows = []
    for feature in features:
        props = feature.get("properties", {})
        rows.append((
            str(get_any(props, "GlobalID", "OBJECTID", "SDE_ID") or ""),
            get_any(props, "material", "MATERIAL", "SURFACE"),
            get_any(props, "condition", "CONDITION"),
            get_any(props, "width_ft", "WIDTH_FT", "WIDTH"),
            synthetic,
            Json(props),
            geom_json(feature),
        ))
    with conn.cursor() as cur:
        cur.executemany(sql, rows)


def load_study_area(conn, features: list[dict[str, Any]], synthetic: bool) -> None:
    sql = """
        INSERT INTO study_area (source_id, name, is_synthetic, raw_properties, geom)
        VALUES (%s, %s, %s, %s, ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)))
    """
    rows = []
    for index, feature in enumerate(features, start=1):
        props = feature.get("properties", {})
        rows.append((
            str(get_any(props, "GlobalID", "OBJECTID", "SDE_ID") or index),
            get_any(props, "name", "NAME", "MUNICIPALITY") or "PACTS Study Area",
            synthetic,
            Json(props),
            geom_json(feature),
        ))
    with conn.cursor() as cur:
        cur.executemany(sql, rows)


def load_neighborhoods(conn, features: list[dict[str, Any]], synthetic: bool) -> None:
    sql = """
        INSERT INTO neighborhoods (
            source_id, name, municipality, population, median_income, is_synthetic, raw_properties, geom
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)))
    """
    rows = []
    for index, feature in enumerate(features, start=1):
        props = feature.get("properties", {})
        rows.append((
            str(get_any(props, "source_id", "GEOID", "OBJECTID") or index),
            get_any(props, "name", "NAME") or f"Neighborhood {index}",
            get_any(props, "municipality", "MUNICIPALITY"),
            int(get_any(props, "population", "POPULATION") or 0),
            get_any(props, "median_income", "MEDIAN_INCOME"),
            synthetic,
            Json(props),
            geom_json(feature),
        ))
    with conn.cursor() as cur:
        cur.executemany(sql, rows)


def load_facilities(conn, table: str, features: list[dict[str, Any]], synthetic: bool) -> None:
    type_column = "school_type" if table == "schools" else "facility_type"
    sql = f"""
        INSERT INTO {table} (source_id, name, {type_column}, is_synthetic, raw_properties, geom)
        VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
    """
    rows = []
    for index, feature in enumerate(features, start=1):
        props = feature.get("properties", {})
        rows.append((
            str(get_any(props, "source_id", "OBJECTID") or index),
            get_any(props, "name", "NAME") or f"{table.title()} {index}",
            get_any(props, "type", "facility_type", "school_type"),
            synthetic,
            Json(props),
            geom_json(feature),
        ))
    with conn.cursor() as cur:
        cur.executemany(sql, rows)


def feature(geometry: dict[str, Any], **properties: Any) -> dict[str, Any]:
    return {"type": "Feature", "properties": properties, "geometry": geometry}


def polygon(minx: float, miny: float, maxx: float, maxy: float) -> dict[str, Any]:
    return {
        "type": "Polygon",
        "coordinates": [[
            [minx, miny],
            [maxx, miny],
            [maxx, maxy],
            [minx, maxy],
            [minx, miny],
        ]],
    }


def line(coords: list[list[float]]) -> dict[str, Any]:
    return {"type": "LineString", "coordinates": coords}


def point(lon: float, lat: float) -> dict[str, Any]:
    return {"type": "Point", "coordinates": [lon, lat]}


def synthetic_features(key: str) -> dict[str, Any]:
    datasets: dict[str, list[dict[str, Any]]] = {
        "study_area": [
            feature(polygon(-70.52, 43.55, -70.18, 43.76), name="Synthetic Greater Portland Study Area", source_id="synthetic-study-area")
        ],
        "neighborhoods": [
            feature(polygon(-70.285, 43.642, -70.245, 43.672), source_id="syn-n-001", name="Portland Peninsula", municipality="Portland", population=18000, median_income=64000),
            feature(polygon(-70.270, 43.675, -70.232, 43.707), source_id="syn-n-002", name="East Deering", municipality="Portland", population=7200, median_income=71000),
            feature(polygon(-70.375, 43.662, -70.325, 43.700), source_id="syn-n-003", name="Westbrook Core", municipality="Westbrook", population=11800, median_income=59000),
            feature(polygon(-70.300, 43.615, -70.225, 43.650), source_id="syn-n-004", name="South Portland Waterfront", municipality="South Portland", population=13500, median_income=68000),
            feature(polygon(-70.282, 43.706, -70.205, 43.750), source_id="syn-n-005", name="Falmouth Foreside", municipality="Falmouth", population=6400, median_income=98000),
            feature(polygon(-70.380, 43.570, -70.292, 43.623), source_id="syn-n-006", name="Scarborough North", municipality="Scarborough", population=9000, median_income=89000),
            feature(polygon(-70.485, 43.645, -70.405, 43.704), source_id="syn-n-007", name="Gorham Center", municipality="Gorham", population=7800, median_income=76000),
        ],
        "schools": [
            feature(point(-70.2597, 43.6548), source_id="syn-s-001", name="Portland High School", type="High School"),
            feature(point(-70.2976, 43.6784), source_id="syn-s-002", name="Deering High School", type="High School"),
            feature(point(-70.3498, 43.6807), source_id="syn-s-003", name="Westbrook High School", type="High School"),
            feature(point(-70.2521, 43.6355), source_id="syn-s-004", name="South Portland High School", type="High School"),
            feature(point(-70.2308, 43.7351), source_id="syn-s-005", name="Falmouth High School", type="High School"),
        ],
        "hospitals": [
            feature(point(-70.2755, 43.6530), source_id="syn-h-001", name="Maine Medical Center", type="Hospital"),
            feature(point(-70.3103, 43.6408), source_id="syn-h-002", name="Northern Light Mercy Hospital", type="Hospital"),
            feature(point(-70.2562, 43.6609), source_id="syn-h-003", name="Mercy Fore River", type="Medical Center"),
        ],
        "transit_stops": [
            feature(point(-70.2589, 43.6573), source_id="syn-ts-001", stop_name="Congress St / Monument Sq", stop_code="SYN-001", route_name="Route 1", IS_HUB=1, IS_WHEELCHAIR_ACCESS=1),
            feature(point(-70.2893, 43.6660), source_id="syn-ts-002", stop_name="Brighton Ave / Deering", stop_code="SYN-002", route_name="Route 2", IS_HUB=0, IS_WHEELCHAIR_ACCESS=1),
            feature(point(-70.3350, 43.6774), source_id="syn-ts-003", stop_name="Westbrook Hub", stop_code="SYN-003", route_name="Route 4", IS_HUB=1, IS_WHEELCHAIR_ACCESS=1),
            feature(point(-70.2505, 43.6383), source_id="syn-ts-004", stop_name="South Portland Mill Creek", stop_code="SYN-004", route_name="Route 21", IS_HUB=0, IS_WHEELCHAIR_ACCESS=1),
        ],
        "transit_routes": [
            feature(line([[-70.290, 43.666], [-70.270, 43.660], [-70.258, 43.657], [-70.245, 43.650]]), source_id="syn-r-001", route_name="Route 1"),
            feature(line([[-70.340, 43.678], [-70.315, 43.672], [-70.290, 43.666], [-70.258, 43.657]]), source_id="syn-r-002", route_name="Route 4"),
            feature(line([[-70.255, 43.638], [-70.250, 43.650], [-70.258, 43.657]]), source_id="syn-r-003", route_name="Route 21"),
        ],
        "sidewalks": [
            feature(line([[-70.286, 43.653], [-70.258, 43.657], [-70.245, 43.662]]), source_id="syn-sw-001", material="Concrete", condition="Good", width_ft=6),
            feature(line([[-70.352, 43.680], [-70.335, 43.677], [-70.325, 43.671]]), source_id="syn-sw-002", material="Asphalt", condition="Fair", width_ft=5),
            feature(line([[-70.270, 43.630], [-70.250, 43.638], [-70.235, 43.645]]), source_id="syn-sw-003", material="Concrete", condition="Good", width_ft=6),
        ],
    }
    return {"type": "FeatureCollection", "features": datasets[key]}


LOADERS = {
    "transit_stops": load_transit_stops,
    "transit_routes": load_transit_routes,
    "sidewalks": load_sidewalks,
    "study_area": load_study_area,
    "neighborhoods": load_neighborhoods,
    "schools": lambda conn, features, synthetic: load_facilities(conn, "schools", features, synthetic),
    "hospitals": lambda conn, features, synthetic: load_facilities(conn, "hospitals", features, synthetic),
}


def save_raw(cfg: dict[str, Any], key: str, payload: dict[str, Any]) -> Path:
    raw_dir = resolve_path(cfg, "raw_dir")
    path = raw_dir / f"{key}.geojson"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def truncate_base_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE " + ", ".join(BASE_TABLES) + " RESTART IDENTITY CASCADE")


def load_source(conn, cfg: dict[str, Any], source: dict[str, Any], synthetic_only: bool = False) -> int:
    key = source["key"]
    synthetic = source.get("loader") == "synthetic" or synthetic_only
    payload: dict[str, Any]

    if synthetic:
        payload = synthetic_features(key)
    else:
        try:
            payload = fetch_arcgis_geojson(source, cfg)
        except Exception as exc:
            if source.get("fallback") != "synthetic":
                raise
            logging.warning("Falling back to synthetic %s data: %s", key, exc)
            payload = synthetic_features(key)
            synthetic = True

    save_raw(cfg, key, payload)
    features = [f for f in payload.get("features", []) if f.get("geometry")]
    if not features:
        logging.warning("No features loaded for %s", key)
        return 0
    LOADERS[key](conn, features, synthetic)
    logging.info("Loaded %s %s features into %s", len(features), key, source["table"])
    return len(features)


def run_etl(config_path: str = "configs/project.toml", synthetic_only: bool = False) -> dict[str, int]:
    cfg = load_config(config_path)
    ensure_directories(cfg)
    setup_logging(cfg)
    counts: dict[str, int] = {}
    with connect(cfg) as conn:
        truncate_base_tables(conn)
        for source in cfg["sources"]:
            counts[source["key"]] = load_source(conn, cfg, source, synthetic_only=synthetic_only)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Download, clean, and load GIS layers into PostGIS.")
    parser.add_argument("--config", default="configs/project.toml")
    parser.add_argument("--synthetic-only", action="store_true", help="Skip live downloads and load synthetic sample data.")
    args = parser.parse_args()

    counts = run_etl(args.config, synthetic_only=args.synthetic_only)
    for key, count in counts.items():
        print(f"{key}: {count}")


if __name__ == "__main__":
    main()
