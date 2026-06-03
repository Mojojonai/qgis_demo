DROP TABLE IF EXISTS underserved_areas CASCADE;
DROP TABLE IF EXISTS neighborhood_accessibility_map CASCADE;
DROP TABLE IF EXISTS town_mobility_need_index CASCADE;
DROP TABLE IF EXISTS mobility_need_index CASCADE;
DROP TABLE IF EXISTS town_accessibility_kpis CASCADE;
DROP TABLE IF EXISTS analysis_unit_accessibility_kpis CASCADE;
DROP TABLE IF EXISTS accessibility_scores CASCADE;
DROP TABLE IF EXISTS neighborhood_facility_counts CASCADE;
DROP TABLE IF EXISTS nearest_facilities CASCADE;
DROP TABLE IF EXISTS nearest_transit_stop CASCADE;
DROP TABLE IF EXISTS neighborhood_sidewalk_access CASCADE;
DROP TABLE IF EXISTS coverage_population CASCADE;
DROP TABLE IF EXISTS coverage_summary CASCADE;
DROP TABLE IF EXISTS coverage_buffers CASCADE;

DROP TABLE IF EXISTS transit_stops CASCADE;
DROP TABLE IF EXISTS transit_routes CASCADE;
DROP TABLE IF EXISTS neighborhoods CASCADE;
DROP TABLE IF EXISTS schools CASCADE;
DROP TABLE IF EXISTS hospitals CASCADE;
DROP TABLE IF EXISTS sidewalks CASCADE;
DROP TABLE IF EXISTS study_area CASCADE;
DROP TABLE IF EXISTS acs_town_demographics CASCADE;

CREATE TABLE transit_routes (
    id bigserial PRIMARY KEY,
    source_id text,
    route_name text,
    agency text,
    is_synthetic boolean NOT NULL DEFAULT false,
    raw_properties jsonb NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(MultiLineString, 4326) NOT NULL
);

CREATE TABLE transit_stops (
    id bigserial PRIMARY KEY,
    source_id text,
    stop_code text,
    stop_name text,
    route_name text,
    is_hub boolean,
    is_on_demand boolean,
    is_school_stop boolean,
    is_wheelchair_accessible boolean,
    is_synthetic boolean NOT NULL DEFAULT false,
    raw_properties jsonb NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(Point, 4326) NOT NULL
);

CREATE TABLE neighborhoods (
    id bigserial PRIMARY KEY,
    source_id text,
    name text NOT NULL,
    municipality text,
    population integer NOT NULL DEFAULT 0,
    median_income numeric,
    is_synthetic boolean NOT NULL DEFAULT false,
    raw_properties jsonb NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(MultiPolygon, 4326) NOT NULL
);

CREATE TABLE schools (
    id bigserial PRIMARY KEY,
    source_id text,
    name text NOT NULL,
    school_type text,
    is_synthetic boolean NOT NULL DEFAULT false,
    raw_properties jsonb NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(Point, 4326) NOT NULL
);

CREATE TABLE hospitals (
    id bigserial PRIMARY KEY,
    source_id text,
    name text NOT NULL,
    facility_type text,
    is_synthetic boolean NOT NULL DEFAULT false,
    raw_properties jsonb NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(Point, 4326) NOT NULL
);

CREATE TABLE sidewalks (
    id bigserial PRIMARY KEY,
    source_id text,
    material text,
    condition text,
    width_ft numeric,
    is_synthetic boolean NOT NULL DEFAULT false,
    raw_properties jsonb NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(MultiLineString, 4326) NOT NULL
);

CREATE TABLE study_area (
    id bigserial PRIMARY KEY,
    source_id text,
    name text NOT NULL,
    is_synthetic boolean NOT NULL DEFAULT false,
    raw_properties jsonb NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(MultiPolygon, 4326) NOT NULL
);

CREATE TABLE acs_town_demographics (
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

CREATE INDEX idx_transit_routes_geom ON transit_routes USING gist (geom);
CREATE INDEX idx_transit_stops_geom ON transit_stops USING gist (geom);
CREATE INDEX idx_neighborhoods_geom ON neighborhoods USING gist (geom);
CREATE INDEX idx_schools_geom ON schools USING gist (geom);
CREATE INDEX idx_hospitals_geom ON hospitals USING gist (geom);
CREATE INDEX idx_sidewalks_geom ON sidewalks USING gist (geom);
CREATE INDEX idx_study_area_geom ON study_area USING gist (geom);
CREATE INDEX idx_acs_town_demographics_town ON acs_town_demographics (lower(town));

COMMENT ON TABLE transit_stops IS 'Transit stop point locations loaded from public ArcGIS REST data or synthetic fallback records.';
COMMENT ON TABLE transit_routes IS 'Transit route linework loaded from public ArcGIS REST data or synthetic fallback records.';
COMMENT ON TABLE neighborhoods IS 'Neighborhood/block-group-like polygons used as the population analysis unit.';
COMMENT ON TABLE sidewalks IS 'Pedestrian network linework used for sidewalk accessibility scoring.';
COMMENT ON TABLE acs_town_demographics IS 'Official ACS 5-year county-subdivision demographic indicators used for mobility-need scoring.';
