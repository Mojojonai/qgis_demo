from __future__ import annotations

import argparse
import io
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable
from urllib.request import Request, urlopen

from psycopg2.extras import Json

from config import ensure_directories, load_config, resolve_path
from db import connect


SENTINELS = {
    "-222222222",
    "-333333333",
    "-555555555",
    "-666666666",
    "-777777777",
    "-888888888",
    "-999999999",
}

TABLES = {
    "B01003": ["B01003_E001"],
    "B01001": [
        "B01001_E020",
        "B01001_E021",
        "B01001_E022",
        "B01001_E023",
        "B01001_E024",
        "B01001_E025",
        "B01001_E044",
        "B01001_E045",
        "B01001_E046",
        "B01001_E047",
        "B01001_E048",
        "B01001_E049",
    ],
    "B17001": ["B17001_E001", "B17001_E002"],
    "B18101": [
        "B18101_E001",
        "B18101_E004",
        "B18101_E007",
        "B18101_E010",
        "B18101_E013",
        "B18101_E016",
        "B18101_E019",
        "B18101_E023",
        "B18101_E026",
        "B18101_E029",
        "B18101_E032",
        "B18101_E035",
        "B18101_E038",
    ],
    "B19013": ["B19013_E001"],
    "B25044": ["B25044_E001", "B25044_E003", "B25044_E010"],
}


def request_text(url: str, timeout: int = 120):
    request = Request(url, headers={"User-Agent": "TransitAccessibilityProject/1.0"})
    response = urlopen(request, timeout=timeout)
    return io.TextIOWrapper(response, encoding="utf-8", errors="replace", newline="")


def clean_town_name(name: str) -> str:
    primary = name.split(",", 1)[0]
    return re.sub(r"\s+(city|town|plantation|unorganized territory)$", "", primary, flags=re.I).strip()


def summary_base(cfg: dict[str, Any]) -> str:
    acs = cfg["acs"]
    return f"{acs['summary_file_base_url'].rstrip('/')}/{acs['year']}/table-based-SF"


def geography_url(cfg: dict[str, Any]) -> str:
    year = cfg["acs"]["year"]
    return f"{summary_base(cfg)}/documentation/Geos{year}5YR.txt"


def table_url(cfg: dict[str, Any], table: str) -> str:
    year = cfg["acs"]["year"]
    return f"{summary_base(cfg)}/data/5YRData/acsdt5y{year}-{table.lower()}.dat"


def find_target_geographies(cfg: dict[str, Any]) -> dict[str, dict[str, str]]:
    acs = cfg["acs"]
    target_towns = {town.lower(): town for town in acs["towns"]}
    targets: dict[str, dict[str, str]] = {}
    with request_text(geography_url(cfg)) as fh:
        header = fh.readline().strip().split("|")
        for line in fh:
            values = line.rstrip("\n").split("|")
            row = dict(zip(header, values))
            if row.get("SUMLEVEL") != "060":
                continue
            if row.get("STATE") != acs["state"] or row.get("COUNTY") != acs["county"]:
                continue
            town = clean_town_name(row.get("NAME", ""))
            if town.lower() not in target_towns:
                continue
            targets[row["GEO_ID"]] = {
                "geoid": row["GEO_ID"],
                "town": target_towns[town.lower()],
                "name": row["NAME"],
                "state_fips": row.get("STATE", ""),
                "county_fips": row.get("COUNTY", ""),
                "county_subdivision_fips": row.get("COUSUB", ""),
            }
            if len(targets) == len(target_towns):
                break
    missing = sorted(set(target_towns.values()) - {row["town"] for row in targets.values()})
    if missing:
        raise RuntimeError(f"Missing ACS county-subdivision geographies for: {', '.join(missing)}")
    return targets


def parse_int(value: str | None) -> int | None:
    if value in (None, "", *SENTINELS):
        return None
    try:
        return int(Decimal(value))
    except Exception:
        return None


def add(values: Iterable[int | None]) -> int | None:
    numbers = [value for value in values if value is not None]
    return sum(numbers) if numbers else None


def pct(part: int | None, total: int | None) -> Decimal | None:
    if part is None or total in (None, 0):
        return None
    return (Decimal(part) / Decimal(total) * Decimal(100)).quantize(Decimal("0.01"))


def fetch_table_values(cfg: dict[str, Any], table: str, geoids: set[str]) -> dict[str, dict[str, int | None]]:
    needed = set(TABLES[table])
    found: dict[str, dict[str, int | None]] = {}
    with request_text(table_url(cfg, table)) as fh:
        header = fh.readline().strip().split("|")
        indexes = {name: header.index(name) for name in needed if name in header}
        if len(indexes) != len(needed):
            missing = sorted(needed - set(indexes))
            raise RuntimeError(f"Missing ACS fields in {table}: {', '.join(missing)}")
        geoid_index = header.index("GEO_ID")
        for line in fh:
            values = line.rstrip("\n").split("|")
            geoid = values[geoid_index]
            if geoid not in geoids:
                continue
            found[geoid] = {field: parse_int(values[index]) for field, index in indexes.items()}
            if len(found) == len(geoids):
                break
    missing_geoids = sorted(geoids - set(found))
    if missing_geoids:
        raise RuntimeError(f"Missing ACS rows in {table}: {', '.join(missing_geoids)}")
    return found


def build_demographics(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    targets = find_target_geographies(cfg)
    geoids = set(targets)
    table_rows = {table: fetch_table_values(cfg, table, geoids) for table in TABLES}

    records: list[dict[str, Any]] = []
    for geoid, geo in sorted(targets.items(), key=lambda item: item[1]["town"]):
        total_population = table_rows["B01003"][geoid]["B01003_E001"]
        population_65_plus = add(table_rows["B01001"][geoid].values())
        poverty_universe = table_rows["B17001"][geoid]["B17001_E001"]
        population_below_poverty = table_rows["B17001"][geoid]["B17001_E002"]
        disability_universe = table_rows["B18101"][geoid]["B18101_E001"]
        population_with_disability = add(
            value
            for field, value in table_rows["B18101"][geoid].items()
            if field != "B18101_E001"
        )
        households = table_rows["B25044"][geoid]["B25044_E001"]
        zero_vehicle_households = add((
            table_rows["B25044"][geoid]["B25044_E003"],
            table_rows["B25044"][geoid]["B25044_E010"],
        ))
        record = {
            **geo,
            "acs_year": int(cfg["acs"]["year"]),
            "total_population": total_population,
            "median_household_income": table_rows["B19013"][geoid]["B19013_E001"],
            "poverty_universe": poverty_universe,
            "population_below_poverty": population_below_poverty,
            "pct_below_poverty": pct(population_below_poverty, poverty_universe),
            "households": households,
            "zero_vehicle_households": zero_vehicle_households,
            "pct_zero_vehicle_households": pct(zero_vehicle_households, households),
            "population_65_plus": population_65_plus,
            "pct_65_plus": pct(population_65_plus, total_population),
            "disability_universe": disability_universe,
            "population_with_disability": population_with_disability,
            "pct_with_disability": pct(population_with_disability, disability_universe),
        }
        record["raw_properties"] = {
            "geography": geo,
            "tables": {table: table_rows[table][geoid] for table in TABLES},
        }
        records.append(record)
    return records


def decimal_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def save_raw(cfg: dict[str, Any], records: list[dict[str, Any]]) -> Path:
    path = resolve_path(cfg, "raw_dir") / "acs_town_demographics.json"
    path.write_text(json.dumps(records, indent=2, default=decimal_default), encoding="utf-8")
    return path


def ensure_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS acs_town_demographics (
                id bigserial PRIMARY KEY,
                geoid text NOT NULL UNIQUE,
                town text NOT NULL,
                name text NOT NULL,
                state_fips text,
                county_fips text,
                county_subdivision_fips text,
                acs_year integer NOT NULL,
                total_population integer,
                median_household_income numeric,
                poverty_universe integer,
                population_below_poverty integer,
                pct_below_poverty numeric,
                households integer,
                zero_vehicle_households integer,
                pct_zero_vehicle_households numeric,
                population_65_plus integer,
                pct_65_plus numeric,
                disability_universe integer,
                population_with_disability integer,
                pct_with_disability numeric,
                raw_properties jsonb NOT NULL DEFAULT '{}'::jsonb
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_acs_town_demographics_town ON acs_town_demographics (lower(town));")


def load_records(cfg: dict[str, Any], records: list[dict[str, Any]]) -> None:
    sql = """
        INSERT INTO acs_town_demographics (
            geoid, town, name, state_fips, county_fips, county_subdivision_fips, acs_year,
            total_population, median_household_income, poverty_universe, population_below_poverty,
            pct_below_poverty, households, zero_vehicle_households, pct_zero_vehicle_households,
            population_65_plus, pct_65_plus, disability_universe, population_with_disability,
            pct_with_disability, raw_properties
        )
        VALUES (
            %(geoid)s, %(town)s, %(name)s, %(state_fips)s, %(county_fips)s, %(county_subdivision_fips)s,
            %(acs_year)s, %(total_population)s, %(median_household_income)s, %(poverty_universe)s,
            %(population_below_poverty)s, %(pct_below_poverty)s, %(households)s,
            %(zero_vehicle_households)s, %(pct_zero_vehicle_households)s, %(population_65_plus)s,
            %(pct_65_plus)s, %(disability_universe)s, %(population_with_disability)s,
            %(pct_with_disability)s, %(raw_properties)s
        )
        ON CONFLICT (geoid) DO UPDATE SET
            town = EXCLUDED.town,
            name = EXCLUDED.name,
            state_fips = EXCLUDED.state_fips,
            county_fips = EXCLUDED.county_fips,
            county_subdivision_fips = EXCLUDED.county_subdivision_fips,
            acs_year = EXCLUDED.acs_year,
            total_population = EXCLUDED.total_population,
            median_household_income = EXCLUDED.median_household_income,
            poverty_universe = EXCLUDED.poverty_universe,
            population_below_poverty = EXCLUDED.population_below_poverty,
            pct_below_poverty = EXCLUDED.pct_below_poverty,
            households = EXCLUDED.households,
            zero_vehicle_households = EXCLUDED.zero_vehicle_households,
            pct_zero_vehicle_households = EXCLUDED.pct_zero_vehicle_households,
            population_65_plus = EXCLUDED.population_65_plus,
            pct_65_plus = EXCLUDED.pct_65_plus,
            disability_universe = EXCLUDED.disability_universe,
            population_with_disability = EXCLUDED.population_with_disability,
            pct_with_disability = EXCLUDED.pct_with_disability,
            raw_properties = EXCLUDED.raw_properties;
    """
    prepared = [{**record, "raw_properties": Json(record["raw_properties"])} for record in records]
    with connect(cfg) as conn:
        ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE acs_town_demographics RESTART IDENTITY;")
            cur.executemany(sql, prepared)


def run_acs_load(config_path: str = "configs/project.toml") -> list[dict[str, Any]]:
    cfg = load_config(config_path)
    ensure_directories(cfg)
    records = build_demographics(cfg)
    save_raw(cfg, records)
    load_records(cfg, records)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Load official ACS town demographics for mobility-need analysis.")
    parser.add_argument("--config", default="configs/project.toml")
    args = parser.parse_args()
    records = run_acs_load(args.config)
    for record in records:
        print(
            f"{record['town']}: population {record['total_population']}, "
            f"zero-car households {record['pct_zero_vehicle_households']}%, "
            f"poverty {record['pct_below_poverty']}%"
        )


if __name__ == "__main__":
    main()
