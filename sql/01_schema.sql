DROP TABLE IF EXISTS underserved_areas CASCADE;
DROP TABLE IF EXISTS neighborhood_accessibility_map CASCADE;
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

CREATE INDEX idx_transit_routes_geom ON transit_routes USING gist (geom);
CREATE INDEX idx_transit_stops_geom ON transit_stops USING gist (geom);
CREATE INDEX idx_neighborhoods_geom ON neighborhoods USING gist (geom);
CREATE INDEX idx_schools_geom ON schools USING gist (geom);
CREATE INDEX idx_hospitals_geom ON hospitals USING gist (geom);
CREATE INDEX idx_sidewalks_geom ON sidewalks USING gist (geom);
CREATE INDEX idx_study_area_geom ON study_area USING gist (geom);

COMMENT ON TABLE transit_stops IS 'Transit stop point locations loaded from public ArcGIS REST data or synthetic fallback records.';
COMMENT ON TABLE transit_routes IS 'Transit route linework loaded from public ArcGIS REST data or synthetic fallback records.';
COMMENT ON TABLE neighborhoods IS 'Neighborhood/block-group-like polygons used as the population analysis unit.';
COMMENT ON TABLE sidewalks IS 'Pedestrian network linework used for sidewalk accessibility scoring.';
