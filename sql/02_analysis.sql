DROP TABLE IF EXISTS underserved_areas CASCADE;
DROP TABLE IF EXISTS neighborhood_accessibility_map CASCADE;
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
    n.geom
FROM neighborhoods n
JOIN accessibility_scores a
    ON a.neighborhood_id = n.id;

CREATE INDEX idx_neighborhood_accessibility_map_geom
ON neighborhood_accessibility_map USING gist (geom);
