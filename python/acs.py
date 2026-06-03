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
        "B01001_E003",
        "B01001_E004",
        "B01001_E005",
        "B01001_E006",
        "B01001_E020",
        "B01001_E021",
        "B01001_E022",
        "B01001_E023",
        "B01001_E024",
        "B01001_E025",
        "B01001_E027",
        "B01001_E028",
        "B01001_E029",
        "B01001_E030",
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
    "B25001": ["B25001_E001"],
    "B25004": ["B25004_E001", "B25004_E006"],
    "B25070": [
        "B25070_E001",
        "B25070_E007",
        "B25070_E008",
        "B25070_E009",
        "B25070_E010",
        "B25070_E011",
    ],
    "B25091": [
        "B25091_E001",
        "B25091_E006",
        "B25091_E007",
        "B25091_E008",
        "B25091_E015",
        "B25091_E016",
        "B25091_E017",
    ],
    "B08301": [
        "B08301_E001",
        "B08301_E003",
        "B08301_E010",
        "B08301_E018",
        "B08301_E019",
        "B08301_E020",
        "B08301_E021",
    ],
    "B08303": [
        "B08303_E001",
        "B08303_E011",
        "B08303_E012",
        "B08303_E013",
    ],
    "B28002": ["B28002_E001", "B28002_E010", "B28002_E011"],
}


AGE_65_PLUS_FIELDS = [
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
]

UNDER_18_FIELDS = [
    "B01001_E003",
    "B01001_E004",
    "B01001_E005",
    "B01001_E006",
    "B01001_E027",
    "B01001_E028",
    "B01001_E029",
    "B01001_E030",
]

RENTER_COST_BURDEN_FIELDS = ["B25070_E007", "B25070_E008", "B25070_E009", "B25070_E010"]
OWNER_COST_BURDEN_FIELDS = ["B25091_E006", "B25091_E007", "B25091_E015", "B25091_E016"]


def request_text(url: str, timeout: int = 300):
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
    target_names = acs.get("towns") or acs.get("focus_towns")
    target_towns = {town.lower(): town for town in target_names} if target_names and acs.get("scope") != "state" else {}
    targets: dict[str, dict[str, str]] = {}
    with request_text(geography_url(cfg)) as fh:
        header = fh.readline().strip().split("|")
        for line in fh:
            values = line.rstrip("\n").split("|")
            row = dict(zip(header, values))
            if row.get("SUMLEVEL") != "060":
                continue
            if row.get("STATE") != acs["state"]:
                continue
            if acs.get("county") and row.get("COUNTY") != acs["county"]:
                continue
            town = clean_town_name(row.get("NAME", ""))
            if target_towns and town.lower() not in target_towns:
                continue
            targets[row["GEO_ID"]] = {
                "geoid": row["GEO_ID"],
                "town": target_towns.get(town.lower(), town),
                "name": row["NAME"],
                "state_fips": row.get("STATE", ""),
                "county_fips": row.get("COUNTY", ""),
                "county_subdivision_fips": row.get("COUSUB", ""),
            }
            if target_towns and len(targets) == len(target_towns):
                break
    if target_towns:
        missing = sorted(set(target_towns.values()) - {row["town"] for row in targets.values()})
        if missing:
            raise RuntimeError(f"Missing ACS county-subdivision geographies for: {', '.join(missing)}")
    if not targets:
        raise RuntimeError("No ACS county-subdivision geographies matched the configured scope.")
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


def subtract(value: int | None, values: Iterable[int | None]) -> int | None:
    if value is None:
        return None
    return value - sum(item for item in values if item is not None)


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
        population_65_plus = add(table_rows["B01001"][geoid][field] for field in AGE_65_PLUS_FIELDS)
        population_under_18 = add(table_rows["B01001"][geoid][field] for field in UNDER_18_FIELDS)
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
        total_housing_units = table_rows["B25001"][geoid]["B25001_E001"]
        vacant_housing_units = table_rows["B25004"][geoid]["B25004_E001"]
        seasonal_housing_units = table_rows["B25004"][geoid]["B25004_E006"]
        renter_cost_universe = subtract(
            table_rows["B25070"][geoid]["B25070_E001"],
            [table_rows["B25070"][geoid]["B25070_E011"]],
        )
        cost_burdened_renter_households = add(table_rows["B25070"][geoid][field] for field in RENTER_COST_BURDEN_FIELDS)
        owner_cost_universe = subtract(
            table_rows["B25091"][geoid]["B25091_E001"],
            [table_rows["B25091"][geoid]["B25091_E008"], table_rows["B25091"][geoid]["B25091_E017"]],
        )
        cost_burdened_owner_households = add(table_rows["B25091"][geoid][field] for field in OWNER_COST_BURDEN_FIELDS)
        cost_burden_household_universe = add((renter_cost_universe, owner_cost_universe))
        cost_burdened_households = add((cost_burdened_renter_households, cost_burdened_owner_households))
        workers_16_plus = table_rows["B08301"][geoid]["B08301_E001"]
        drove_alone_workers = table_rows["B08301"][geoid]["B08301_E003"]
        public_transport_workers = table_rows["B08301"][geoid]["B08301_E010"]
        walk_bike_workers = add((table_rows["B08301"][geoid]["B08301_E018"], table_rows["B08301"][geoid]["B08301_E019"]))
        other_non_car_workers = table_rows["B08301"][geoid]["B08301_E020"]
        work_from_home_workers = table_rows["B08301"][geoid]["B08301_E021"]
        long_commute_workers = add((
            table_rows["B08303"][geoid]["B08303_E011"],
            table_rows["B08303"][geoid]["B08303_E012"],
            table_rows["B08303"][geoid]["B08303_E013"],
        ))
        internet_households = table_rows["B28002"][geoid]["B28002_E001"]
        no_internet_households = table_rows["B28002"][geoid]["B28002_E011"]
        no_internet_or_subscription_households = add((
            table_rows["B28002"][geoid]["B28002_E010"],
            table_rows["B28002"][geoid]["B28002_E011"],
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
            "population_under_18": population_under_18,
            "pct_under_18": pct(population_under_18, total_population),
            "disability_universe": disability_universe,
            "population_with_disability": population_with_disability,
            "pct_with_disability": pct(population_with_disability, disability_universe),
            "total_housing_units": total_housing_units,
            "vacant_housing_units": vacant_housing_units,
            "pct_vacant_housing_units": pct(vacant_housing_units, total_housing_units),
            "seasonal_housing_units": seasonal_housing_units,
            "pct_seasonal_housing_units": pct(seasonal_housing_units, total_housing_units),
            "renter_cost_universe": renter_cost_universe,
            "cost_burdened_renter_households": cost_burdened_renter_households,
            "pct_cost_burdened_renter_households": pct(cost_burdened_renter_households, renter_cost_universe),
            "owner_cost_universe": owner_cost_universe,
            "cost_burdened_owner_households": cost_burdened_owner_households,
            "pct_cost_burdened_owner_households": pct(cost_burdened_owner_households, owner_cost_universe),
            "cost_burden_household_universe": cost_burden_household_universe,
            "cost_burdened_households": cost_burdened_households,
            "pct_cost_burdened_households": pct(cost_burdened_households, cost_burden_household_universe),
            "workers_16_plus": workers_16_plus,
            "drove_alone_workers": drove_alone_workers,
            "pct_drove_alone_workers": pct(drove_alone_workers, workers_16_plus),
            "public_transport_workers": public_transport_workers,
            "pct_public_transport_workers": pct(public_transport_workers, workers_16_plus),
            "walk_bike_workers": walk_bike_workers,
            "pct_walk_bike_workers": pct(walk_bike_workers, workers_16_plus),
            "other_non_car_workers": other_non_car_workers,
            "work_from_home_workers": work_from_home_workers,
            "pct_work_from_home_workers": pct(work_from_home_workers, workers_16_plus),
            "long_commute_workers": long_commute_workers,
            "pct_long_commute_workers": pct(long_commute_workers, workers_16_plus),
            "internet_households": internet_households,
            "no_internet_households": no_internet_households,
            "pct_no_internet_households": pct(no_internet_households, internet_households),
            "no_internet_or_subscription_households": no_internet_or_subscription_households,
            "pct_no_internet_or_subscription_households": pct(no_internet_or_subscription_households, internet_households),
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
                population_under_18 integer,
                pct_under_18 numeric,
                disability_universe integer,
                population_with_disability integer,
                pct_with_disability numeric,
                total_housing_units integer,
                vacant_housing_units integer,
                pct_vacant_housing_units numeric,
                seasonal_housing_units integer,
                pct_seasonal_housing_units numeric,
                renter_cost_universe integer,
                cost_burdened_renter_households integer,
                pct_cost_burdened_renter_households numeric,
                owner_cost_universe integer,
                cost_burdened_owner_households integer,
                pct_cost_burdened_owner_households numeric,
                cost_burden_household_universe integer,
                cost_burdened_households integer,
                pct_cost_burdened_households numeric,
                workers_16_plus integer,
                drove_alone_workers integer,
                pct_drove_alone_workers numeric,
                public_transport_workers integer,
                pct_public_transport_workers numeric,
                walk_bike_workers integer,
                pct_walk_bike_workers numeric,
                other_non_car_workers integer,
                work_from_home_workers integer,
                pct_work_from_home_workers numeric,
                long_commute_workers integer,
                pct_long_commute_workers numeric,
                internet_households integer,
                no_internet_households integer,
                pct_no_internet_households numeric,
                no_internet_or_subscription_households integer,
                pct_no_internet_or_subscription_households numeric,
                raw_properties jsonb NOT NULL DEFAULT '{}'::jsonb
            );
        """)
        for column, data_type in [
            ("population_under_18", "integer"),
            ("pct_under_18", "numeric"),
            ("total_housing_units", "integer"),
            ("vacant_housing_units", "integer"),
            ("pct_vacant_housing_units", "numeric"),
            ("seasonal_housing_units", "integer"),
            ("pct_seasonal_housing_units", "numeric"),
            ("renter_cost_universe", "integer"),
            ("cost_burdened_renter_households", "integer"),
            ("pct_cost_burdened_renter_households", "numeric"),
            ("owner_cost_universe", "integer"),
            ("cost_burdened_owner_households", "integer"),
            ("pct_cost_burdened_owner_households", "numeric"),
            ("cost_burden_household_universe", "integer"),
            ("cost_burdened_households", "integer"),
            ("pct_cost_burdened_households", "numeric"),
            ("workers_16_plus", "integer"),
            ("drove_alone_workers", "integer"),
            ("pct_drove_alone_workers", "numeric"),
            ("public_transport_workers", "integer"),
            ("pct_public_transport_workers", "numeric"),
            ("walk_bike_workers", "integer"),
            ("pct_walk_bike_workers", "numeric"),
            ("other_non_car_workers", "integer"),
            ("work_from_home_workers", "integer"),
            ("pct_work_from_home_workers", "numeric"),
            ("long_commute_workers", "integer"),
            ("pct_long_commute_workers", "numeric"),
            ("internet_households", "integer"),
            ("no_internet_households", "integer"),
            ("pct_no_internet_households", "numeric"),
            ("no_internet_or_subscription_households", "integer"),
            ("pct_no_internet_or_subscription_households", "numeric"),
        ]:
            cur.execute(f"ALTER TABLE acs_town_demographics ADD COLUMN IF NOT EXISTS {column} {data_type};")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_acs_town_demographics_town ON acs_town_demographics (lower(town));")


def load_records(cfg: dict[str, Any], records: list[dict[str, Any]]) -> None:
    sql = """
        INSERT INTO acs_town_demographics (
            geoid, town, name, state_fips, county_fips, county_subdivision_fips, acs_year,
            total_population, median_household_income, poverty_universe, population_below_poverty,
            pct_below_poverty, households, zero_vehicle_households, pct_zero_vehicle_households,
            population_65_plus, pct_65_plus, population_under_18, pct_under_18,
            disability_universe, population_with_disability, pct_with_disability,
            total_housing_units, vacant_housing_units, pct_vacant_housing_units,
            seasonal_housing_units, pct_seasonal_housing_units, renter_cost_universe,
            cost_burdened_renter_households, pct_cost_burdened_renter_households,
            owner_cost_universe, cost_burdened_owner_households, pct_cost_burdened_owner_households,
            cost_burden_household_universe, cost_burdened_households, pct_cost_burdened_households,
            workers_16_plus, drove_alone_workers, pct_drove_alone_workers,
            public_transport_workers, pct_public_transport_workers, walk_bike_workers,
            pct_walk_bike_workers, other_non_car_workers, work_from_home_workers,
            pct_work_from_home_workers, long_commute_workers, pct_long_commute_workers,
            internet_households, no_internet_households, pct_no_internet_households,
            no_internet_or_subscription_households, pct_no_internet_or_subscription_households,
            raw_properties
        )
        VALUES (
            %(geoid)s, %(town)s, %(name)s, %(state_fips)s, %(county_fips)s, %(county_subdivision_fips)s,
            %(acs_year)s, %(total_population)s, %(median_household_income)s, %(poverty_universe)s,
            %(population_below_poverty)s, %(pct_below_poverty)s, %(households)s,
            %(zero_vehicle_households)s, %(pct_zero_vehicle_households)s, %(population_65_plus)s,
            %(pct_65_plus)s, %(population_under_18)s, %(pct_under_18)s, %(disability_universe)s,
            %(population_with_disability)s, %(pct_with_disability)s,
            %(total_housing_units)s, %(vacant_housing_units)s, %(pct_vacant_housing_units)s,
            %(seasonal_housing_units)s, %(pct_seasonal_housing_units)s, %(renter_cost_universe)s,
            %(cost_burdened_renter_households)s, %(pct_cost_burdened_renter_households)s,
            %(owner_cost_universe)s, %(cost_burdened_owner_households)s, %(pct_cost_burdened_owner_households)s,
            %(cost_burden_household_universe)s, %(cost_burdened_households)s, %(pct_cost_burdened_households)s,
            %(workers_16_plus)s, %(drove_alone_workers)s, %(pct_drove_alone_workers)s,
            %(public_transport_workers)s, %(pct_public_transport_workers)s, %(walk_bike_workers)s,
            %(pct_walk_bike_workers)s, %(other_non_car_workers)s, %(work_from_home_workers)s,
            %(pct_work_from_home_workers)s, %(long_commute_workers)s, %(pct_long_commute_workers)s,
            %(internet_households)s, %(no_internet_households)s, %(pct_no_internet_households)s,
            %(no_internet_or_subscription_households)s, %(pct_no_internet_or_subscription_households)s,
            %(raw_properties)s
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
            population_under_18 = EXCLUDED.population_under_18,
            pct_under_18 = EXCLUDED.pct_under_18,
            disability_universe = EXCLUDED.disability_universe,
            population_with_disability = EXCLUDED.population_with_disability,
            pct_with_disability = EXCLUDED.pct_with_disability,
            total_housing_units = EXCLUDED.total_housing_units,
            vacant_housing_units = EXCLUDED.vacant_housing_units,
            pct_vacant_housing_units = EXCLUDED.pct_vacant_housing_units,
            seasonal_housing_units = EXCLUDED.seasonal_housing_units,
            pct_seasonal_housing_units = EXCLUDED.pct_seasonal_housing_units,
            renter_cost_universe = EXCLUDED.renter_cost_universe,
            cost_burdened_renter_households = EXCLUDED.cost_burdened_renter_households,
            pct_cost_burdened_renter_households = EXCLUDED.pct_cost_burdened_renter_households,
            owner_cost_universe = EXCLUDED.owner_cost_universe,
            cost_burdened_owner_households = EXCLUDED.cost_burdened_owner_households,
            pct_cost_burdened_owner_households = EXCLUDED.pct_cost_burdened_owner_households,
            cost_burden_household_universe = EXCLUDED.cost_burden_household_universe,
            cost_burdened_households = EXCLUDED.cost_burdened_households,
            pct_cost_burdened_households = EXCLUDED.pct_cost_burdened_households,
            workers_16_plus = EXCLUDED.workers_16_plus,
            drove_alone_workers = EXCLUDED.drove_alone_workers,
            pct_drove_alone_workers = EXCLUDED.pct_drove_alone_workers,
            public_transport_workers = EXCLUDED.public_transport_workers,
            pct_public_transport_workers = EXCLUDED.pct_public_transport_workers,
            walk_bike_workers = EXCLUDED.walk_bike_workers,
            pct_walk_bike_workers = EXCLUDED.pct_walk_bike_workers,
            other_non_car_workers = EXCLUDED.other_non_car_workers,
            work_from_home_workers = EXCLUDED.work_from_home_workers,
            pct_work_from_home_workers = EXCLUDED.pct_work_from_home_workers,
            long_commute_workers = EXCLUDED.long_commute_workers,
            pct_long_commute_workers = EXCLUDED.pct_long_commute_workers,
            internet_households = EXCLUDED.internet_households,
            no_internet_households = EXCLUDED.no_internet_households,
            pct_no_internet_households = EXCLUDED.pct_no_internet_households,
            no_internet_or_subscription_households = EXCLUDED.no_internet_or_subscription_households,
            pct_no_internet_or_subscription_households = EXCLUDED.pct_no_internet_or_subscription_households,
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
    print(f"Loaded {len(records)} ACS county-subdivision records.")
    focus_towns = set(load_config(args.config).get("acs", {}).get("focus_towns", []))
    for record in records:
        if record["town"] in focus_towns:
            print(
                f"{record['town']}: population {record['total_population']}, "
                f"zero-car households {record['pct_zero_vehicle_households']}%, "
                f"poverty {record['pct_below_poverty']}%"
            )


if __name__ == "__main__":
    main()
