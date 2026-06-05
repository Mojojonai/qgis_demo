-- Build planning-grade candidate grid units for the Maine climate-safe housing workflow.
-- This is a screening model, not a parcel/build permit decision.

DELETE FROM climate_housing_candidate_units
WHERE unit_type = 'statewide_5km_grid';

WITH params AS (
    SELECT
        5000.0::numeric AS grid_size_m,
        5070::integer AS analysis_srid
),
town_scores AS (
    SELECT DISTINCT ON (lower(town), lower(county))
        lower(town) AS town_key,
        lower(county) AS county_key,
        town,
        county,
        acs_population,
        housing_need_score,
        social_vulnerability_score,
        infrastructure_efficiency_proxy_score,
        resilience_investment_priority_score,
        climate_safe_housing_mvp_score
    FROM climate_housing_town_screening
    ORDER BY lower(town), lower(county), source_year DESC NULLS LAST
),
towns AS (
    SELECT
        b.geoid,
        b.town,
        b.county,
        ST_Transform(b.geom, (SELECT analysis_srid FROM params)) AS geom_5070,
        b.geom AS geom_4326,
        s.acs_population,
        COALESCE(s.housing_need_score, 0) AS housing_need_score,
        COALESCE(s.social_vulnerability_score, 0) AS social_vulnerability_score,
        COALESCE(s.infrastructure_efficiency_proxy_score, 0) AS infrastructure_efficiency_proxy_score,
        COALESCE(s.resilience_investment_priority_score, 0) AS resilience_investment_priority_score,
        COALESCE(s.climate_safe_housing_mvp_score, 0) AS climate_safe_housing_mvp_score
    FROM climate_housing_town_boundaries b
    JOIN town_scores s
      ON lower(b.town) = s.town_key
     AND lower(b.county) = s.county_key
    WHERE COALESCE(s.acs_population, 0) > 0
),
analysis_extent AS (
    SELECT
        ST_Extent(geom_5070)::box2d AS extent
    FROM towns
),
bounds AS (
    SELECT
        (floor(ST_XMin(extent)::numeric / (SELECT grid_size_m FROM params)) * (SELECT grid_size_m FROM params)) AS xmin,
        (ceil(ST_XMax(extent)::numeric / (SELECT grid_size_m FROM params)) * (SELECT grid_size_m FROM params)) AS xmax,
        (floor(ST_YMin(extent)::numeric / (SELECT grid_size_m FROM params)) * (SELECT grid_size_m FROM params)) AS ymin,
        (ceil(ST_YMax(extent)::numeric / (SELECT grid_size_m FROM params)) * (SELECT grid_size_m FROM params)) AS ymax
    FROM analysis_extent
),
grid AS (
    SELECT
        row_number() OVER () AS grid_id,
        ST_SetSRID(
            ST_MakeEnvelope(
                x::double precision,
                y::double precision,
                (x + (SELECT grid_size_m FROM params))::double precision,
                (y + (SELECT grid_size_m FROM params))::double precision
            ),
            (SELECT analysis_srid FROM params)
        ) AS geom_5070
    FROM bounds,
         generate_series(xmin, xmax, (SELECT grid_size_m FROM params)) AS x,
         generate_series(ymin, ymax, (SELECT grid_size_m FROM params)) AS y
),
grid_town_intersections AS (
    SELECT
        g.grid_id,
        t.geoid AS town_geoid,
        t.town,
        t.county,
        t.acs_population,
        t.housing_need_score,
        t.social_vulnerability_score,
        t.infrastructure_efficiency_proxy_score,
        t.resilience_investment_priority_score,
        t.climate_safe_housing_mvp_score,
        ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_Intersection(g.geom_5070, t.geom_5070)), 3)) AS geom_5070
    FROM grid g
    JOIN towns t
      ON ST_Intersects(g.geom_5070, t.geom_5070)
),
candidate_base AS (
    SELECT
        grid_id,
        town_geoid,
        town,
        county,
        acs_population,
        housing_need_score,
        social_vulnerability_score,
        infrastructure_efficiency_proxy_score,
        resilience_investment_priority_score,
        climate_safe_housing_mvp_score,
        ST_Area(geom_5070) AS buildable_area_sq_m,
        geom_5070,
        ST_Transform(geom_5070, 4326) AS geom_4326
    FROM grid_town_intersections
    WHERE NOT ST_IsEmpty(geom_5070)
      AND ST_Area(geom_5070) >= 250000
),
hazard_exposure AS (
    SELECT
        c.grid_id,
        c.town_geoid,
        COUNT(h.id) AS hazard_polygon_count,
        COALESCE(
            SUM(
                ST_Area(
                    ST_Intersection(c.geom_5070, ST_Transform(h.geom, (SELECT analysis_srid FROM params)))
                )
            ),
            0
        ) AS hazard_area_sq_m
    FROM candidate_base c
    LEFT JOIN climate_housing_hazard_zones h
      ON ST_Intersects(c.geom_4326, h.geom)
    GROUP BY c.grid_id, c.town_geoid, c.geom_5070
),
environmental_exposure AS (
    SELECT
        c.grid_id,
        c.town_geoid,
        COUNT(e.id) AS environmental_polygon_count,
        COALESCE(
            SUM(
                ST_Area(
                    ST_Intersection(c.geom_5070, ST_Transform(e.geom, (SELECT analysis_srid FROM params)))
                )
            ),
            0
        ) AS environmental_area_sq_m
    FROM candidate_base c
    LEFT JOIN climate_housing_environmental_constraints e
      ON ST_Intersects(c.geom_4326, e.geom)
    GROUP BY c.grid_id, c.town_geoid, c.geom_5070
),
asset_exposure AS (
    SELECT
        c.grid_id,
        c.town_geoid,
        COUNT(a.id) AS climate_asset_count,
        COUNT(a.id) FILTER (WHERE a.asset_type ILIKE '%slr%' OR a.asset_type ILIKE '%flood%') AS flood_slr_asset_count,
        COUNT(a.id) FILTER (WHERE a.asset_type IN ('bridge', 'cross_culvert')) AS road_structure_count
    FROM candidate_base c
    LEFT JOIN climate_housing_infrastructure_assets a
      ON ST_DWithin(
          ST_Transform(c.geom_4326, (SELECT analysis_srid FROM params)),
          ST_Transform(a.geom, (SELECT analysis_srid FROM params)),
          1000
      )
    GROUP BY c.grid_id, c.town_geoid
),
scored AS (
    SELECT
        c.*,
        COALESCE(h.hazard_polygon_count, 0) AS hazard_polygon_count,
        COALESCE(h.hazard_area_sq_m, 0) AS hazard_area_sq_m,
        COALESCE(e.environmental_polygon_count, 0) AS environmental_polygon_count,
        COALESCE(e.environmental_area_sq_m, 0) AS environmental_area_sq_m,
        COALESCE(a.climate_asset_count, 0) AS climate_asset_count,
        COALESCE(a.flood_slr_asset_count, 0) AS flood_slr_asset_count,
        COALESCE(a.road_structure_count, 0) AS road_structure_count,
        LEAST(
            100,
            COALESCE(h.hazard_area_sq_m, 0) / NULLIF(c.buildable_area_sq_m, 0) * 100
            + COALESCE(a.flood_slr_asset_count, 0) * 8
        ) AS flood_exposure_score,
        LEAST(
            100,
            COALESCE(e.environmental_area_sq_m, 0) / NULLIF(c.buildable_area_sq_m, 0) * 100
        ) AS environmental_constraint_score,
        LEAST(100, GREATEST(0, c.infrastructure_efficiency_proxy_score + LEAST(15, COALESCE(a.road_structure_count, 0) * 2))) AS infrastructure_access_score
    FROM candidate_base c
    LEFT JOIN hazard_exposure h
      ON h.grid_id = c.grid_id
     AND h.town_geoid = c.town_geoid
    LEFT JOIN environmental_exposure e
      ON e.grid_id = c.grid_id
     AND e.town_geoid = c.town_geoid
    LEFT JOIN asset_exposure a
      ON a.grid_id = c.grid_id
     AND a.town_geoid = c.town_geoid
),
final_scores AS (
    SELECT
        *,
        round((
            housing_need_score * 0.30
            + infrastructure_access_score * 0.30
            + (100 - flood_exposure_score) * 0.20
            + (100 - environmental_constraint_score) * 0.10
            + (100 - social_vulnerability_score) * 0.10
        )::numeric, 2) AS climate_safe_suitability_score
    FROM scored
)
INSERT INTO climate_housing_candidate_units (
    unit_id,
    unit_type,
    town,
    county,
    tract_geoid,
    buildable_area_sq_m,
    excluded_area_sq_m,
    flood_exposure_score,
    environmental_constraint_score,
    infrastructure_access_score,
    social_vulnerability_score,
    housing_need_score,
    climate_safe_suitability_score,
    suitability_tier,
    review_notes,
    raw_properties,
    geom
)
SELECT
    concat('grid5km_', town_geoid, '_', grid_id) AS unit_id,
    'statewide_5km_grid' AS unit_type,
    town,
    county,
    NULL AS tract_geoid,
    buildable_area_sq_m,
    CASE
        WHEN environmental_constraint_score >= 70 THEN buildable_area_sq_m
        WHEN flood_exposure_score >= 80 THEN buildable_area_sq_m * 0.75
        WHEN environmental_constraint_score >= 40 OR flood_exposure_score >= 50 THEN buildable_area_sq_m * 0.35
        ELSE 0
    END AS excluded_area_sq_m,
    flood_exposure_score,
    environmental_constraint_score,
    infrastructure_access_score,
    social_vulnerability_score,
    housing_need_score,
    climate_safe_suitability_score,
    CASE
        WHEN flood_exposure_score >= 80 OR environmental_constraint_score >= 70 THEN 'avoid or detailed hazard review'
        WHEN climate_safe_suitability_score >= 70 THEN 'strong candidate for parcel screening'
        WHEN climate_safe_suitability_score >= 58 THEN 'moderate candidate for parcel screening'
        WHEN housing_need_score >= 60 AND social_vulnerability_score >= 60 THEN 'resilience before growth'
        ELSE 'monitor after full overlays'
    END AS suitability_tier,
    CASE
        WHEN flood_exposure_score >= 80 OR environmental_constraint_score >= 70 THEN 'Potential exposure/constraint signal; do not classify as build-ready without parcel-scale flood, wetland, conservation, slope, and zoning review.'
        WHEN climate_safe_suitability_score >= 70 THEN 'High planning score; prioritize parcel-level confirmation and affordability safeguards.'
        WHEN climate_safe_suitability_score >= 58 THEN 'Moderate planning score; compare with local infrastructure, zoning, and hazard overlays.'
        WHEN housing_need_score >= 60 AND social_vulnerability_score >= 60 THEN 'Need and vulnerability overlap; pair housing work with resilience and anti-displacement investment.'
        ELSE 'Keep in monitoring queue until full hazard and environmental overlays are complete.'
    END AS review_notes,
    jsonb_build_object(
        'analysis_grid_size_m', (SELECT grid_size_m FROM params),
        'town_geoid', town_geoid,
        'acs_population', acs_population,
        'climate_safe_housing_mvp_score', climate_safe_housing_mvp_score,
        'resilience_investment_priority_score', resilience_investment_priority_score,
        'hazard_polygon_count', hazard_polygon_count,
        'hazard_area_sq_m', round(hazard_area_sq_m::numeric, 2),
        'environmental_polygon_count', environmental_polygon_count,
        'environmental_area_sq_m', round(environmental_area_sq_m::numeric, 2),
        'climate_asset_count', climate_asset_count,
        'flood_slr_asset_count', flood_slr_asset_count,
        'road_structure_count', road_structure_count
    ) AS raw_properties,
    ST_Transform(geom_5070, 4326) AS geom
FROM final_scores;
