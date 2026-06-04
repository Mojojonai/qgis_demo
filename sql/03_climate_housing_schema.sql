CREATE TABLE IF NOT EXISTS climate_housing_hazard_zones (
    id bigserial PRIMARY KEY,
    source_name text NOT NULL,
    hazard_type text NOT NULL,
    scenario text,
    hazard_class text,
    effective_date date,
    source_url text,
    raw_properties jsonb NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(MultiPolygon, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS climate_housing_environmental_constraints (
    id bigserial PRIMARY KEY,
    source_name text NOT NULL,
    constraint_type text NOT NULL,
    constraint_class text,
    regulatory_status text,
    source_url text,
    raw_properties jsonb NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(MultiPolygon, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS climate_housing_infrastructure_assets (
    id bigserial PRIMARY KEY,
    source_name text NOT NULL,
    asset_type text NOT NULL,
    asset_name text,
    owner text,
    condition_rating text,
    source_url text,
    raw_properties jsonb NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(Geometry, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS climate_housing_candidate_units (
    id bigserial PRIMARY KEY,
    unit_id text,
    unit_type text NOT NULL,
    town text,
    county text,
    tract_geoid text,
    buildable_area_sq_m numeric,
    excluded_area_sq_m numeric,
    flood_exposure_score numeric,
    environmental_constraint_score numeric,
    infrastructure_access_score numeric,
    social_vulnerability_score numeric,
    housing_need_score numeric,
    climate_safe_suitability_score numeric,
    suitability_tier text,
    review_notes text,
    raw_properties jsonb NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(Geometry, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS climate_housing_town_screening (
    id bigserial PRIMARY KEY,
    town text NOT NULL,
    county text NOT NULL,
    acs_population integer,
    housing_need_score numeric,
    social_vulnerability_score numeric,
    infrastructure_efficiency_proxy_score numeric,
    resilience_investment_priority_score numeric,
    climate_safe_housing_mvp_score numeric,
    mvp_priority_lane text,
    hazard_overlay_status text,
    key_drivers text[],
    source_year integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (town, county, source_year)
);

CREATE INDEX IF NOT EXISTS idx_climate_housing_hazard_zones_geom
    ON climate_housing_hazard_zones USING gist (geom);

CREATE INDEX IF NOT EXISTS idx_climate_housing_environmental_constraints_geom
    ON climate_housing_environmental_constraints USING gist (geom);

CREATE INDEX IF NOT EXISTS idx_climate_housing_infrastructure_assets_geom
    ON climate_housing_infrastructure_assets USING gist (geom);

CREATE INDEX IF NOT EXISTS idx_climate_housing_candidate_units_geom
    ON climate_housing_candidate_units USING gist (geom);

CREATE INDEX IF NOT EXISTS idx_climate_housing_town_screening_town
    ON climate_housing_town_screening (lower(town), lower(county));

COMMENT ON TABLE climate_housing_hazard_zones IS 'Future-ingest table for FEMA NFHL, Maine Geological Survey sea-level-rise/storm-surge, riverine flood, and related hazard zones.';
COMMENT ON TABLE climate_housing_environmental_constraints IS 'Future-ingest table for wetlands, conserved lands, shoreland zones, habitat, steep-slope masks, and related development constraints.';
COMMENT ON TABLE climate_housing_infrastructure_assets IS 'Future-ingest table for roads, bridges, culverts, wastewater, water, critical facilities, broadband, and other infrastructure assets.';
COMMENT ON TABLE climate_housing_candidate_units IS 'Parcel, grid-cell, or tract-level candidate units for full climate-safe housing suitability modeling.';
COMMENT ON TABLE climate_housing_town_screening IS 'Town-level same-day MVP screening scores built from statewide ACS indicators before parcel/hazard overlay ingestion.';
