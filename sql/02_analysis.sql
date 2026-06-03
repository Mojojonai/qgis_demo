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
DROP TABLE IF EXISTS coverage_buffers CASCADE;
DROP TABLE IF EXISTS coverage_summary CASCADE;

-- Analysis 1: 400 m and 800 m transit coverage buffers.
-- ST_Buffer uses EPSG:26919 so buffer distances are measured in meters.
CREATE TABLE coverage_buffers AS
SELECT
    buffer_m,
    ST_Multi(
        ST_Transform(
            ST_Union(ST_Buffer(ST_Transform(geom, 26919), buffer_m)),
            4326
        )
    )::geometry(MultiPolygon, 4326) AS geom
FROM transit_stops
CROSS JOIN (VALUES (400), (800)) AS distances(buffer_m)
GROUP BY buffer_m;

CREATE INDEX idx_coverage_buffers_geom ON coverage_buffers USING gist (geom);

-- Estimate covered population by intersecting neighborhood polygons with each
-- coverage buffer. Partial coverage is area-weighted.
CREATE TABLE coverage_population AS
WITH neighborhood_m AS (
    SELECT
        id,
        name,
        population,
        ST_Transform(geom, 26919) AS geom_m,
        NULLIF(ST_Area(ST_Transform(geom, 26919)), 0) AS area_m2
    FROM neighborhoods
),
coverage_m AS (
    SELECT buffer_m, ST_Transform(geom, 26919) AS geom_m
    FROM coverage_buffers
)
SELECT
    c.buffer_m,
    ROUND(SUM(n.population * COALESCE(ST_Area(ST_Intersection(n.geom_m, c.geom_m)) / n.area_m2, 0))::numeric, 0)::integer AS population_inside,
    SUM(n.population)::integer - ROUND(SUM(n.population * COALESCE(ST_Area(ST_Intersection(n.geom_m, c.geom_m)) / n.area_m2, 0))::numeric, 0)::integer AS population_outside,
    SUM(n.population)::integer AS total_population
FROM coverage_m c
CROSS JOIN neighborhood_m n
GROUP BY c.buffer_m;

CREATE TABLE coverage_summary AS
SELECT
    buffer_m,
    population_inside,
    population_outside,
    total_population,
    ROUND((population_inside::numeric / NULLIF(total_population, 0)) * 100, 2) AS pct_population_inside
FROM coverage_population;

-- Analysis 2: nearest transit stop by neighborhood centroid.
-- The ORDER BY expression demonstrates KNN-style nearest-neighbor search.
CREATE TABLE nearest_transit_stop AS
SELECT
    n.id AS neighborhood_id,
    n.name AS neighborhood_name,
    s.id AS transit_stop_id,
    s.stop_name,
    s.route_name,
    ROUND(
        ST_Distance(
            ST_Transform(ST_Centroid(n.geom), 26919),
            ST_Transform(s.geom, 26919)
        )::numeric,
        2
    ) AS distance_m,
    ST_DWithin(
        ST_Transform(ST_Centroid(n.geom), 26919),
        ST_Transform(s.geom, 26919),
        800
    ) AS within_800m
FROM neighborhoods n
CROSS JOIN LATERAL (
    SELECT id, stop_name, route_name, geom
    FROM transit_stops
    ORDER BY ST_Centroid(n.geom) <-> geom
    LIMIT 1
) s;

-- Sidewalk access: total sidewalk length intersecting each neighborhood.
CREATE TABLE neighborhood_sidewalk_access AS
WITH neighborhood_m AS (
    SELECT id, name, ST_Transform(geom, 26919) AS geom_m
    FROM neighborhoods
)
SELECT
    n.id AS neighborhood_id,
    n.name AS neighborhood_name,
    ROUND(
        COALESCE(SUM(ST_Length(ST_Intersection(ST_Transform(sw.geom, 26919), n.geom_m))), 0)::numeric,
        2
    ) AS sidewalk_m
FROM neighborhood_m n
LEFT JOIN sidewalks sw
    ON ST_Intersects(sw.geom, ST_Transform(n.geom_m, 4326))
GROUP BY n.id, n.name;

-- Facility counts use both ST_Contains and ST_Within to make the spatial
-- relationship explicit for review and portfolio discussion.
CREATE TABLE neighborhood_facility_counts AS
SELECT
    n.id AS neighborhood_id,
    n.name AS neighborhood_name,
    COUNT(DISTINCT sc.id) FILTER (
        WHERE ST_Contains(n.geom, sc.geom) OR ST_Within(sc.geom, n.geom)
    ) AS schools_inside,
    COUNT(DISTINCT h.id) FILTER (
        WHERE ST_Contains(n.geom, h.geom) OR ST_Within(h.geom, n.geom)
    ) AS hospitals_inside
FROM neighborhoods n
LEFT JOIN schools sc
    ON ST_Intersects(n.geom, sc.geom)
LEFT JOIN hospitals h
    ON ST_Intersects(n.geom, h.geom)
GROUP BY n.id, n.name;

CREATE TABLE nearest_facilities AS
SELECT
    n.id AS neighborhood_id,
    n.name AS neighborhood_name,
    school.id AS nearest_school_id,
    school.name AS nearest_school_name,
    ROUND(school.distance_m::numeric, 2) AS nearest_school_distance_m,
    hospital.id AS nearest_hospital_id,
    hospital.name AS nearest_hospital_name,
    ROUND(hospital.distance_m::numeric, 2) AS nearest_hospital_distance_m
FROM neighborhoods n
CROSS JOIN LATERAL (
    SELECT
        id,
        name,
        ST_Distance(ST_Transform(ST_Centroid(n.geom), 26919), ST_Transform(geom, 26919)) AS distance_m
    FROM schools
    ORDER BY ST_Centroid(n.geom) <-> geom
    LIMIT 1
) school
CROSS JOIN LATERAL (
    SELECT
        id,
        name,
        ST_Distance(ST_Transform(ST_Centroid(n.geom), 26919), ST_Transform(geom, 26919)) AS distance_m
    FROM hospitals
    ORDER BY ST_Centroid(n.geom) <-> geom
    LIMIT 1
) hospital;

-- Analysis 3: weighted accessibility score from 0 to 100.
CREATE TABLE accessibility_scores AS
WITH sidewalk_norm AS (
    SELECT
        neighborhood_id,
        neighborhood_name,
        sidewalk_m,
        CASE
            WHEN MAX(sidewalk_m) OVER () = 0 THEN 0
            ELSE LEAST(100, (sidewalk_m / MAX(sidewalk_m) OVER ()) * 100)
        END AS sidewalk_score
    FROM neighborhood_sidewalk_access
),
scores AS (
    SELECT
        n.id AS neighborhood_id,
        n.name AS neighborhood_name,
        n.population,
        nt.distance_m AS nearest_stop_distance_m,
        CASE
            WHEN nt.distance_m <= 400 THEN 100
            WHEN nt.distance_m <= 800 THEN 70
            WHEN nt.distance_m <= 1600 THEN GREATEST(0, 70 - ((nt.distance_m - 800) / 800) * 70)
            ELSE 0
        END AS transit_score,
        sn.sidewalk_score,
        nf.nearest_school_distance_m,
        GREATEST(0, LEAST(100, 100 - (nf.nearest_school_distance_m / 1600) * 100)) AS school_score,
        nf.nearest_hospital_distance_m,
        GREATEST(0, LEAST(100, 100 - (nf.nearest_hospital_distance_m / 3200) * 100)) AS hospital_score
    FROM neighborhoods n
    JOIN nearest_transit_stop nt ON nt.neighborhood_id = n.id
    JOIN sidewalk_norm sn ON sn.neighborhood_id = n.id
    JOIN nearest_facilities nf ON nf.neighborhood_id = n.id
)
SELECT
    neighborhood_id,
    neighborhood_name,
    population,
    ROUND(nearest_stop_distance_m::numeric, 2) AS nearest_stop_distance_m,
    ROUND(transit_score::numeric, 2) AS transit_score,
    ROUND(sidewalk_score::numeric, 2) AS sidewalk_score,
    ROUND(school_score::numeric, 2) AS school_score,
    ROUND(hospital_score::numeric, 2) AS hospital_score,
    ROUND((0.40 * transit_score + 0.30 * sidewalk_score + 0.20 * school_score + 0.10 * hospital_score)::numeric, 2) AS accessibility_score
FROM scores;

-- Analysis 4: underserved area ranking.
CREATE TABLE underserved_areas AS
SELECT
    ROW_NUMBER() OVER (ORDER BY a.accessibility_score ASC, a.nearest_stop_distance_m DESC) AS underserved_rank,
    a.*,
    NOT EXISTS (
        SELECT 1
        FROM coverage_buffers b
        JOIN neighborhoods n ON n.id = a.neighborhood_id
        WHERE b.buffer_m = 800
          AND ST_Intersects(n.geom, b.geom)
    ) AS outside_800m_buffer,
    a.accessibility_score < 40 AS score_below_40,
    a.nearest_stop_distance_m > 800 AS farther_than_800m
FROM accessibility_scores a
WHERE a.accessibility_score < 40
   OR a.nearest_stop_distance_m > 800
   OR NOT EXISTS (
        SELECT 1
        FROM coverage_buffers b
        JOIN neighborhoods n ON n.id = a.neighborhood_id
        WHERE b.buffer_m = 800
          AND ST_Intersects(n.geom, b.geom)
   );

CREATE INDEX idx_accessibility_scores_neighborhood ON accessibility_scores (neighborhood_id);
CREATE INDEX idx_underserved_rank ON underserved_areas (underserved_rank);

-- Analysis 5: report-ready KPI tables for every town and analysis unit.
-- These tables support full report coverage, not just strongest/weakest examples.
CREATE TABLE analysis_unit_accessibility_kpis AS
WITH coverage_by_neighborhood AS (
    SELECT
        n.id AS neighborhood_id,
        c.buffer_m,
        ROUND(
            (
                n.population
                * COALESCE(ST_Area(ST_Intersection(n.geom_m, c.geom_m)) / n.area_m2, 0)
            )::numeric,
            0
        )::integer AS population_inside,
        ROUND(
            (
                COALESCE(ST_Area(ST_Intersection(n.geom_m, c.geom_m)) / n.area_m2, 0)
                * 100
            )::numeric,
            2
        ) AS pct_population_inside
    FROM (
        SELECT
            id,
            population,
            ST_Transform(geom, 26919) AS geom_m,
            NULLIF(ST_Area(ST_Transform(geom, 26919)), 0) AS area_m2
        FROM neighborhoods
    ) n
    CROSS JOIN (
        SELECT buffer_m, ST_Transform(geom, 26919) AS geom_m
        FROM coverage_buffers
    ) c
),
coverage_pivot AS (
    SELECT
        neighborhood_id,
        COALESCE(MAX(population_inside) FILTER (WHERE buffer_m = 400), 0) AS population_400m,
        COALESCE(MAX(pct_population_inside) FILTER (WHERE buffer_m = 400), 0) AS pct_pop_400m,
        COALESCE(MAX(population_inside) FILTER (WHERE buffer_m = 800), 0) AS population_800m,
        COALESCE(MAX(pct_population_inside) FILTER (WHERE buffer_m = 800), 0) AS pct_pop_800m
    FROM coverage_by_neighborhood
    GROUP BY neighborhood_id
),
unit_base AS (
    SELECT
        n.id AS neighborhood_id,
        COALESCE(NULLIF(n.municipality, ''), n.name) AS town,
        n.name AS analysis_unit,
        n.population,
        COALESCE(acs.median_household_income, n.median_income) AS median_income,
        acs.geoid AS acs_geoid,
        acs.acs_year,
        acs.total_population AS acs_town_population,
        acs.pct_below_poverty,
        acs.pct_zero_vehicle_households,
        acs.pct_65_plus,
        acs.pct_with_disability,
        n.is_synthetic,
        cp.population_400m,
        cp.pct_pop_400m,
        cp.population_800m,
        cp.pct_pop_800m,
        nt.stop_name AS nearest_stop_name,
        nt.route_name AS nearest_route_name,
        a.nearest_stop_distance_m,
        nt.within_800m,
        a.accessibility_score,
        a.transit_score,
        a.sidewalk_score,
        a.school_score,
        a.hospital_score,
        swa.sidewalk_m,
        ROUND((swa.sidewalk_m / 1000)::numeric, 2) AS sidewalk_km,
        ROUND(((swa.sidewalk_m / NULLIF(n.population, 0)) * 1000)::numeric, 2) AS sidewalk_m_per_1000_residents,
        nfc.schools_inside,
        nfc.hospitals_inside,
        nf.nearest_school_name,
        nf.nearest_school_distance_m,
        nf.nearest_hospital_name,
        nf.nearest_hospital_distance_m,
        EXISTS (
            SELECT 1
            FROM underserved_areas u
            WHERE u.neighborhood_id = n.id
        ) AS is_underserved,
        CASE
            WHEN a.transit_score = LEAST(a.transit_score, a.sidewalk_score, a.school_score, a.hospital_score) THEN 'Transit'
            WHEN a.sidewalk_score = LEAST(a.transit_score, a.sidewalk_score, a.school_score, a.hospital_score) THEN 'Sidewalk'
            WHEN a.school_score = LEAST(a.transit_score, a.sidewalk_score, a.school_score, a.hospital_score) THEN 'School'
            ELSE 'Hospital'
        END AS lowest_scoring_dimension,
        CASE
            WHEN a.accessibility_score >= 80 THEN 'High'
            WHEN a.accessibility_score >= 60 THEN 'Moderate-high'
            WHEN a.accessibility_score >= 40 THEN 'Moderate'
            ELSE 'Low'
        END AS access_category
    FROM neighborhoods n
    JOIN accessibility_scores a ON a.neighborhood_id = n.id
    JOIN nearest_transit_stop nt ON nt.neighborhood_id = n.id
    JOIN neighborhood_sidewalk_access swa ON swa.neighborhood_id = n.id
    JOIN neighborhood_facility_counts nfc ON nfc.neighborhood_id = n.id
    JOIN nearest_facilities nf ON nf.neighborhood_id = n.id
    JOIN coverage_pivot cp ON cp.neighborhood_id = n.id
    LEFT JOIN acs_town_demographics acs
        ON lower(acs.town) = lower(COALESCE(NULLIF(n.municipality, ''), n.name))
)
SELECT
    ROW_NUMBER() OVER (ORDER BY accessibility_score DESC, nearest_stop_distance_m ASC) AS accessibility_rank,
    *
FROM unit_base;

CREATE TABLE town_accessibility_kpis AS
WITH town_rollup AS (
    SELECT
        town,
        COUNT(*) AS analysis_units,
        SUM(population)::integer AS total_population,
        SUM(population_400m)::integer AS population_400m,
        ROUND((SUM(population_400m)::numeric / NULLIF(SUM(population), 0)) * 100, 2) AS pct_pop_400m,
        SUM(population_800m)::integer AS population_800m,
        ROUND((SUM(population_800m)::numeric / NULLIF(SUM(population), 0)) * 100, 2) AS pct_pop_800m,
        ROUND((SUM(accessibility_score * population)::numeric / NULLIF(SUM(population), 0)), 2) AS weighted_accessibility_score,
        ROUND(AVG(accessibility_score)::numeric, 2) AS avg_accessibility_score,
        ROUND(MIN(accessibility_score)::numeric, 2) AS min_accessibility_score,
        ROUND(MAX(accessibility_score)::numeric, 2) AS max_accessibility_score,
        ROUND(AVG(nearest_stop_distance_m)::numeric, 2) AS avg_nearest_stop_m,
        ROUND(MAX(nearest_stop_distance_m)::numeric, 2) AS max_nearest_stop_m,
        ROUND(AVG(transit_score)::numeric, 2) AS avg_transit_score,
        ROUND(AVG(sidewalk_score)::numeric, 2) AS avg_sidewalk_score,
        ROUND(AVG(school_score)::numeric, 2) AS avg_school_score,
        ROUND(AVG(hospital_score)::numeric, 2) AS avg_hospital_score,
        ROUND((SUM(sidewalk_m)::numeric / 1000), 2) AS sidewalk_km,
        ROUND(((SUM(sidewalk_m)::numeric / NULLIF(SUM(population), 0)) * 1000), 2) AS sidewalk_m_per_1000_residents,
        MAX(acs_town_population)::integer AS acs_town_population,
        MAX(median_income) AS median_household_income,
        ROUND(MAX(pct_below_poverty)::numeric, 2) AS pct_below_poverty,
        ROUND(MAX(pct_zero_vehicle_households)::numeric, 2) AS pct_zero_vehicle_households,
        ROUND(MAX(pct_65_plus)::numeric, 2) AS pct_65_plus,
        ROUND(MAX(pct_with_disability)::numeric, 2) AS pct_with_disability,
        SUM(schools_inside)::integer AS schools_inside,
        SUM(hospitals_inside)::integer AS hospitals_inside,
        COUNT(*) FILTER (WHERE within_800m)::integer AS units_within_800m,
        COUNT(*) FILTER (WHERE NOT within_800m)::integer AS units_farther_than_800m,
        COUNT(*) FILTER (WHERE is_underserved)::integer AS underserved_units,
        COUNT(*) FILTER (WHERE is_synthetic)::integer AS synthetic_units
    FROM analysis_unit_accessibility_kpis
    GROUP BY town
)
SELECT
    ROW_NUMBER() OVER (ORDER BY weighted_accessibility_score DESC, avg_nearest_stop_m ASC) AS town_rank,
    *
FROM town_rollup;

CREATE INDEX idx_analysis_unit_accessibility_kpis_town ON analysis_unit_accessibility_kpis (town);
CREATE INDEX idx_town_accessibility_kpis_rank ON town_accessibility_kpis (town_rank);

-- Analysis 6: Mobility Need Index.
-- Higher scores identify places where transportation gaps overlap with
-- demographic vulnerability measured from official ACS 5-year data.
CREATE TABLE mobility_need_index AS
WITH components AS (
    SELECT
        k.*,
        ROUND((100 - k.accessibility_score)::numeric, 2) AS accessibility_gap_score,
        COALESCE(k.pct_zero_vehicle_households, 0) AS zero_vehicle_need_score,
        COALESCE(k.pct_below_poverty, 0) AS poverty_need_score,
        COALESCE(k.pct_65_plus, 0) AS older_adult_need_score,
        COALESCE(k.pct_with_disability, 0) AS disability_need_score
    FROM analysis_unit_accessibility_kpis k
),
indexed AS (
    SELECT
        *,
        ROUND((
            0.30 * accessibility_gap_score
            + 0.20 * zero_vehicle_need_score
            + 0.20 * poverty_need_score
            + 0.15 * older_adult_need_score
            + 0.15 * disability_need_score
        )::numeric, 2) AS mobility_need_index
    FROM components
)
SELECT
    ROW_NUMBER() OVER (ORDER BY mobility_need_index DESC, accessibility_gap_score DESC) AS mobility_need_rank,
    *,
    CASE
        WHEN mobility_need_index >= 40 THEN 'Critical'
        WHEN mobility_need_index >= 30 THEN 'High'
        WHEN mobility_need_index >= 20 THEN 'Elevated'
        ELSE 'Monitor'
    END AS priority_tier,
    CASE
        WHEN accessibility_gap_score = GREATEST(accessibility_gap_score, zero_vehicle_need_score, poverty_need_score, older_adult_need_score, disability_need_score) THEN 'Access gap'
        WHEN zero_vehicle_need_score = GREATEST(accessibility_gap_score, zero_vehicle_need_score, poverty_need_score, older_adult_need_score, disability_need_score) THEN 'Zero-car households'
        WHEN poverty_need_score = GREATEST(accessibility_gap_score, zero_vehicle_need_score, poverty_need_score, older_adult_need_score, disability_need_score) THEN 'Poverty'
        WHEN older_adult_need_score = GREATEST(accessibility_gap_score, zero_vehicle_need_score, poverty_need_score, older_adult_need_score, disability_need_score) THEN 'Older adults'
        ELSE 'Disability'
    END AS primary_need_driver
FROM indexed;

CREATE TABLE town_mobility_need_index AS
WITH town_rollup AS (
    SELECT
        town,
        COUNT(*) AS analysis_units,
        SUM(population)::integer AS sample_population,
        MAX(acs_town_population)::integer AS acs_town_population,
        ROUND((SUM(mobility_need_index * population)::numeric / NULLIF(SUM(population), 0)), 2) AS weighted_mobility_need_index,
        ROUND(AVG(mobility_need_index)::numeric, 2) AS avg_mobility_need_index,
        ROUND(MAX(mobility_need_index)::numeric, 2) AS max_mobility_need_index,
        ROUND((SUM(accessibility_score * population)::numeric / NULLIF(SUM(population), 0)), 2) AS weighted_accessibility_score,
        ROUND(MAX(pct_below_poverty)::numeric, 2) AS pct_below_poverty,
        ROUND(MAX(pct_zero_vehicle_households)::numeric, 2) AS pct_zero_vehicle_households,
        ROUND(MAX(pct_65_plus)::numeric, 2) AS pct_65_plus,
        ROUND(MAX(pct_with_disability)::numeric, 2) AS pct_with_disability,
        ROUND(AVG(accessibility_gap_score)::numeric, 2) AS avg_accessibility_gap_score,
        ROUND(AVG(nearest_stop_distance_m)::numeric, 2) AS avg_nearest_stop_m,
        COUNT(*) FILTER (WHERE priority_tier IN ('Critical', 'High'))::integer AS high_need_units,
        COUNT(*) FILTER (WHERE is_underserved)::integer AS underserved_units,
        MODE() WITHIN GROUP (ORDER BY primary_need_driver) AS dominant_need_driver
    FROM mobility_need_index
    GROUP BY town
)
SELECT
    ROW_NUMBER() OVER (ORDER BY weighted_mobility_need_index DESC, avg_accessibility_gap_score DESC) AS mobility_need_town_rank,
    *
FROM town_rollup;

CREATE INDEX idx_mobility_need_index_rank ON mobility_need_index (mobility_need_rank);
CREATE INDEX idx_town_mobility_need_index_rank ON town_mobility_need_index (mobility_need_town_rank);

-- Geometry-bearing map table for QGIS symbology.
CREATE TABLE neighborhood_accessibility_map AS
SELECT
    n.id,
    n.source_id,
    n.name,
    n.municipality,
    n.population,
    n.is_synthetic,
    a.nearest_stop_distance_m,
    a.transit_score,
    a.sidewalk_score,
    a.school_score,
    a.hospital_score,
    a.accessibility_score,
    m.mobility_need_index,
    m.priority_tier,
    m.primary_need_driver,
    n.geom
FROM neighborhoods n
JOIN accessibility_scores a
    ON a.neighborhood_id = n.id
LEFT JOIN mobility_need_index m
    ON m.neighborhood_id = n.id;

CREATE INDEX idx_neighborhood_accessibility_map_geom
ON neighborhood_accessibility_map USING gist (geom);
