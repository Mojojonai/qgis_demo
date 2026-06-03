# GIS-Based Identification of Climate-Safe Housing Growth Areas in Maine

## 1. Research Title And Abstract

**Title:** GIS-Based Identification of Climate-Safe Housing Growth Areas in Maine: Integrating Flood Risk, Infrastructure Capacity, Environmental Constraints, and Social Vulnerability

**Abstract:**  
Maine faces two pressures that must be planned together: a serious need for new housing and rising climate risk along coastal, riverine, and low-lying communities. This project proposes an open-source geospatial decision-support workflow to identify where Maine can add housing while avoiding flood exposure, sea-level-rise inundation, storm-surge zones, wetlands, conservation land, steep slopes, and infrastructure-limited areas. The analysis integrates Maine-specific public datasets from the Maine GeoLibrary, Maine Geological Survey, FEMA, USGS 3DEP, Census ACS, MaineDOT, USFWS, CDC/ATSDR, and state housing/planning sources. Using QGIS, PostGIS, Python, GeoPandas, Rasterio, WhiteboxTools, PySAL, OSMnx/NetworkX, and MapLibre/Leaflet dashboards, the project will produce parcel, grid-cell, census-tract, and municipal screening outputs. A multi-criteria suitability model will score candidate growth areas using climate safety, environmental permissibility, road and service accessibility, terrain, land-cover compatibility, and proximity to existing town centers. A companion vulnerability index will rank communities where housing need, social vulnerability, climate exposure, and infrastructure fragility overlap. Expected outputs include static publication maps, interactive web maps, ranked town and tract tables, suitability rasters, priority investment zones, and a reproducible data pipeline. The result is not a development permit map; it is a planning-grade screening system that helps state agencies, regional planners, towns, housing organizations, and residents ask better questions: where should Maine grow, where should it not grow, and where should public resilience investment come first?

## 2. Problem Statement

Maine needs more housing, but adding homes in the wrong places can deepen future risk. Coastal towns face sea-level rise, storm surge, tidal flooding, erosion, and wetland constraints. Inland towns face riverine flooding, undersized culverts, steep terrain, long emergency-response distances, limited sewer/water capacity, limited broadband, and high transportation costs. Many rural and coastal communities also have older populations, lower-income households, high seasonal-housing pressure, and limited access to services.

The public question is no longer simply "where is land vacant?" The better question is: **where can Maine build housing that is safer over the long term, affordable to households, efficient for infrastructure, and respectful of environmental limits?**

This research matters because Maine municipalities need practical, map-based evidence for comprehensive plans, housing production goals, resilience grants, capital improvement planning, shoreland and floodplain policy, conservation decisions, and infrastructure investment. A transparent open-source GIS workflow can help towns compare locations using the same logic, while still allowing local planners to adjust weights based on local conditions.

## 3. Research Questions

**Main Research Question:**  
Where are the most suitable climate-safe housing growth areas in Maine when flood risk, sea-level rise, storm surge, wetlands, conservation land, terrain, infrastructure access, housing need, and social vulnerability are evaluated together?

**Sub-questions:**

1. Which parcels, grid cells, census tracts, or towns should be excluded from new housing growth because of flood hazard, sea-level-rise/storm-surge exposure, wetlands, conserved land, steep slope, or other environmental constraints?
2. Where do housing need and climate risk overlap most strongly?
3. Which communities have high social vulnerability and limited infrastructure resilience, and therefore need public investment before or alongside housing growth?
4. Which areas are close enough to existing roads, town centers, public services, utilities, schools, transit, or employment centers to support infrastructure-efficient housing?
5. How sensitive are "best growth areas" to different policy priorities, such as affordability-first, climate-safety-first, infrastructure-efficiency-first, or conservation-first weighting?
6. Which map products are most useful for municipal planners, state agencies, housing developers, and the public?

## 4. Conceptual Framework

```text
Housing Need
  - cost burden
  - overcrowding
  - renter pressure
  - population/workforce demand
  - seasonal housing pressure
        |
        v
Candidate Growth Demand
        |
        +------------------+
        |                  |
        v                  v
Climate Risk          Environmental Constraints
  - FEMA flood zones     - wetlands
  - sea-level rise       - conserved land
  - storm surge          - shoreland buffers
  - low elevation        - critical habitats
  - erosion              - steep slopes
        |                  |
        +---------+--------+
                  v
       Buildable/Safe Land Filter
                  |
                  v
Infrastructure Capacity And Access
  - road access
  - bridge/culvert exposure
  - water/sewer where available
  - town-center proximity
  - schools/healthcare/critical facilities
  - broadband
                  |
                  v
Social Vulnerability And Equity
  - low income
  - age 65+
  - disability
  - no vehicle
  - language/tenure vulnerability
  - manufactured/mobile home exposure
                  |
                  v
Policy Outputs
  - climate-safe housing suitability
  - avoid-development zones
  - resilience investment zones
  - housing need/risk overlap
  - municipal priority rankings
```

The framework separates **exclusionary constraints** from **scored suitability**. Floodways, open water, wetlands, conserved land, and extreme hazard zones may remove land from consideration. Remaining candidate land is scored for relative suitability. Social vulnerability is not treated as a reason to avoid investment; it is used to prioritize equitable resilience and housing support.

## 5. Data Inventory

| Dataset | Source | Spatial Scale | Geometry | Update Frequency | Purpose |
| --- | --- | --- | --- | --- | --- |
| Maine municipal boundaries | Maine GeoLibrary | Statewide municipal | Polygon | Periodic | Summarize results by town and align outputs with local governments. |
| Census tracts/block groups | U.S. Census TIGER/Line | Statewide | Polygon | Annual/decennial | Social vulnerability and housing need units. |
| ACS 5-year demographics/housing | U.S. Census Bureau ACS API/Summary File | Tract, block group, county subdivision | Table joined to boundaries | Annual | Housing cost burden, poverty, age, disability, no-vehicle households, tenure, vacancy, commute. |
| CDC/ATSDR Social Vulnerability Index | CDC/ATSDR SVI | County/tract | Polygon/table | Every 2 years historically | External vulnerability benchmark and validation layer. |
| FEMA National Flood Hazard Layer | FEMA Map Service Center/NFHL | Parcel/tract/town overlay | Polygon | Updated as FIRMs change | Regulatory flood zones, floodway, VE/AE zones, base flood exposure. |
| Maine sea-level-rise/storm-surge layers | Maine Geological Survey | Coastal statewide | Polygon | Scenario-based, periodic | Future coastal inundation scenarios and planning exclusions. |
| Highest Astronomical Tide | Maine Geological Survey | Coastal statewide | Polygon | Scenario-based, periodic | Coastal baseline exposure and tidal inundation context. |
| USGS 3DEP DEM/LiDAR | USGS 3DEP / The National Map | Raster, high resolution where available | Raster/point cloud | Ongoing national updates | Elevation, slope, low-lying land, hydrologic derivatives, 3D terrain. |
| MaineDOT public roads | MaineDOT OpenData | Statewide road network | Line | Regular service updates | Road access, network accessibility, evacuation and service routes. |
| MaineDOT bridges | MaineDOT OpenData | Statewide structures | Point/line | Regular service updates | Infrastructure vulnerability and bridge exposure. |
| MaineDOT cross culverts/large culverts | MaineDOT OpenData | Statewide structures | Point | Regular service updates | Flood-sensitive transportation infrastructure. |
| E911 roads | Maine GeoLibrary / Maine E911 | Statewide road centerlines | Line | Regular updates | Addressable road access, emergency response, local network completeness. |
| National Wetlands Inventory | USFWS NWI | Statewide | Polygon | Updated biannually in mapper/downloads where new data exist | Wetland exclusion, buffers, environmental review. |
| Conservation lands | Maine Bureau of Parks and Lands / Maine GeoLibrary | Statewide | Polygon | Periodic | Remove protected/conserved land from housing suitability. |
| Maine high-resolution land cover or NLCD | Maine GeoLibrary / NOAA / USGS NLCD | Statewide raster | Raster | Maine project/annual NLCD where available | Developed land, forest, agriculture, open land, imperviousness, constraint classes. |
| Parcels | Maine GeoLibrary / municipal parcel sources | Town/partial statewide | Polygon | Varies by municipality | Parcel-level candidate-site screening where available. |
| Zoning and shoreland zoning | Municipal/LUPC/DEP sources where available | Municipal or unorganized territory | Polygon | Varies | Legal/planning feasibility and shoreland constraints. |
| Critical facilities | Maine GeoLibrary, HIFLD, local/state sources | Statewide or local | Point/polygon | Varies | Schools, hospitals, emergency services, shelters, wastewater plants. |
| Public water/sewer service areas | Municipal utilities, Maine DEP, local GIS | Local/regional | Polygon/line/point | Varies | Infrastructure capacity proxy and buildout feasibility. |
| OpenStreetMap amenities | OSM via OSMnx | Statewide/local | Point/line/polygon | Continuously edited | Supplemental services, walkability, town-center context. |
| Housing production need | MaineHousing/GOPIF/DECD study | State/region | Table | Study-based | Calibrate housing demand and policy framing. |
| Historic flood events/high-water marks | USGS, FEMA, NOAA, local emergency management | Event/local | Point/polygon | Event-based | Validation of flood exposure logic. |

## 6. Reproducible Open-Source GIS Workflow

### Phase A: Study Design And Data Setup

1. Define study units: statewide 30 m grid for raster screening, census tracts/block groups for vulnerability, municipalities for policy summaries, and parcels where available.
2. Create a PostGIS database:
   ```sql
   CREATE DATABASE maine_climate_housing;
   CREATE EXTENSION postgis;
   CREATE EXTENSION postgis_raster;
   CREATE EXTENSION pg_trgm;
   ```
3. Use a common projected CRS for analysis: `EPSG:26919` for UTM Zone 19N or Maine State Plane East/West zones for local studies. Use `EPSG:4326` only for web publishing.
4. Build folder structure:
   ```text
   data/raw/
   data/processed/
   data/interim/
   sql/
   notebooks/
   reports/
   web/
   qgis/
   ```

### Phase B: Data Collection

1. Pull vector layers from ArcGIS REST services using Python `requests`, `pyogrio`, `geopandas`, or `ogr2ogr`.
2. Download FEMA NFHL for Maine or stream NFHL as WFS/REST where appropriate.
3. Download Maine Geological Survey sea-level-rise/storm-surge shapefiles for coastal scenarios.
4. Download USGS 3DEP DEM tiles or use National Map/3DEP services for DEM derivatives.
5. Download NWI wetlands by state or HUC8 from USFWS.
6. Pull ACS variables from the Census API or table-based Summary File. Required groups include demographics, income, tenure, cost burden, no-vehicle households, age, disability, vacancy, and commute.
7. Collect parcel and zoning data for pilot municipalities if statewide parcel/zoning coverage is incomplete.

### Phase C: Normalize And Load

1. Reproject all layers to analysis CRS.
2. Repair geometries with `ST_MakeValid`, `ogr2ogr -makevalid`, or QGIS Fix Geometries.
3. Standardize names and IDs: `geoid`, `town`, `county`, `source`, `update_date`.
4. Load to PostGIS:
   ```bash
   ogr2ogr -f PostgreSQL PG:"dbname=maine_climate_housing" data/processed/fema_nfhl.gpkg -nln fema_nfhl -overwrite
   ogr2ogr -f PostgreSQL PG:"dbname=maine_climate_housing" data/processed/wetlands.gpkg -nln wetlands -overwrite
   ```
5. Create spatial indexes:
   ```sql
   CREATE INDEX ON fema_nfhl USING gist (geom);
   CREATE INDEX ON wetlands USING gist (geom);
   CREATE INDEX ON parcels USING gist (geom);
   ```

### Phase D: Exclusion Mask

Create a hard exclusion layer:

- FEMA floodway.
- FEMA VE and high-risk AE zones, depending on policy scenario.
- MGS sea-level-rise/storm-surge inundation scenarios, especially higher planning scenarios.
- Open water.
- NWI wetlands plus regulatory buffer, where appropriate.
- Conserved/protected land.
- Very steep slopes, such as greater than 15 percent or 20 percent.
- Shoreland zones where development is legally constrained.
- Parcels already developed beyond selected threshold, if the focus is greenfield capacity.

PostGIS pattern:

```sql
CREATE TABLE hard_exclusion AS
SELECT ST_UnaryUnion(ST_Collect(geom)) AS geom
FROM (
    SELECT geom FROM fema_nfhl WHERE flood_zone IN ('VE', 'AE', 'A', 'AO', 'FLOODWAY')
    UNION ALL
    SELECT geom FROM slr_storm_surge WHERE scenario IN ('slr_3_9ft', 'slr_6_1ft', 'slr_8_8ft')
    UNION ALL
    SELECT geom FROM wetlands
    UNION ALL
    SELECT geom FROM conservation_lands
) x;
```

### Phase E: Candidate Growth Units

1. If parcel data exists: remove excluded area from parcels and calculate buildable share.
2. If parcel data is incomplete: create a statewide grid, such as 30 m, 100 m, or 250 m cells.
3. Attach town, tract, flood, terrain, land cover, road access, service access, and vulnerability attributes.
4. Create a `candidate_growth_units` table with one row per parcel or grid cell.

### Phase F: Suitability Scoring

1. Reclassify continuous variables to 0-100.
2. Apply weights using SQL or Python.
3. Run multiple scenarios:
   - Baseline balanced.
   - Climate-safety-first.
   - Affordability/equity-first.
   - Infrastructure-efficiency-first.
   - Conservation-first.
4. Output candidate units classified as:
   - Tier 1: strong climate-safe growth candidate.
   - Tier 2: conditional candidate, requires local review.
   - Tier 3: low suitability.
   - Avoid: excluded or high-risk.

### Phase G: Vulnerability And Investment Priority

1. Build vulnerability index at tract, block group, and town levels.
2. Intersect vulnerability with flood exposure and housing need.
3. Rank priority resilience investment zones.
4. Identify places where housing should be added only after resilience or infrastructure upgrades.

### Phase H: Visualization And Publishing

1. QGIS for static cartography and map layouts.
2. MapLibre GL JS or Leaflet for interactive maps.
3. deck.gl or kepler.gl for high-volume point/grid exploration.
4. Apache Superset, Observable Framework, Streamlit, Dash, or Panel for dashboards.
5. pg_tileserv or GeoServer for serving PostGIS layers.

## 7. Suitability Model

**Candidate Suitability Score, 0-100:**

```text
Suitability =
  0.25 Climate Safety
+ 0.20 Infrastructure Efficiency
+ 0.15 Environmental Compatibility
+ 0.15 Housing Need Alignment
+ 0.10 Social Equity Benefit
+ 0.10 Terrain And Land-Cover Suitability
+ 0.05 Local Planning Feasibility
```

### Indicator Definitions

| Component | Indicators | Scoring Logic |
| --- | --- | --- |
| Climate Safety | Outside FEMA SFHA, outside floodway, outside MGS SLR/storm-surge scenarios, higher elevation above tidal/flood surfaces | High score if outside exposure zones and above elevation thresholds. |
| Infrastructure Efficiency | Distance to public roads, town centers, sewer/water where available, schools, healthcare, jobs, transit, broadband | Higher score near existing infrastructure but not inside hazard zones. |
| Environmental Compatibility | Avoids wetlands, conserved land, high-value habitat, riparian buffers, shoreland constraints | Higher score for already disturbed or low-conflict land. |
| Housing Need Alignment | Town/tract housing cost burden, low vacancy for year-round housing, workforce demand, renter pressure | Higher score where need is high and land is safe. |
| Social Equity Benefit | High vulnerability plus safe-accessible site, without displacement pressure | Higher score when housing can serve vulnerable households in low-risk areas. |
| Terrain/Land Cover | Gentle slopes, non-wetland open/developed land, low forest fragmentation impact | Higher score for slopes under 8 percent and compatible land cover. |
| Planning Feasibility | Zoning allows residential/mixed use, parcel size, infill potential, municipal growth areas | Higher score where local policy supports housing. |

### Hard Exclusions

No matter how high other scores are, set final suitability to `Avoid` if:

- In FEMA floodway.
- In open water or mapped wetland.
- In conserved/protected land not available for development.
- In high-confidence SLR/storm-surge inundation scenario selected for the policy case.
- Slope exceeds threshold, such as 20 percent.
- Parcel has no legal access or is below minimum buildable area after constraints.

## 8. Vulnerability Index

**Community Vulnerability Index, 0-100:**

```text
Vulnerability =
  0.25 Social Vulnerability
+ 0.20 Housing Stress
+ 0.20 Climate Exposure
+ 0.15 Infrastructure Fragility
+ 0.10 Mobility Constraint
+ 0.10 Recovery Capacity Gap
```

| Component | Example Variables | Unit |
| --- | --- | --- |
| Social Vulnerability | poverty, age 65+, disability, limited English, single-parent households, renters | Tract/block group/town |
| Housing Stress | renter cost burden, owner cost burden, overcrowding, seasonal/vacant pressure, older housing stock | Tract/town |
| Climate Exposure | share of land/buildings/population in FEMA SFHA, SLR/storm surge, low elevation, flood-prone roads | Tract/town |
| Infrastructure Fragility | exposed roads, bridges, culverts, wastewater plants, emergency facilities | Tract/town/network segment |
| Mobility Constraint | no-vehicle households, long commute, distance to services, limited transit | Tract/town |
| Recovery Capacity Gap | low income, older adults, disability, no broadband/internet, distance to critical facilities | Tract/town |

Use CDC/ATSDR SVI as both an input option and an external validation benchmark. For transparency, build a local ACS-based version as well, so users can inspect every variable.

## 9. Spatial Analysis Methods

### Flood Exposure Analysis

- Intersect parcels/buildings/grid cells with FEMA NFHL zones.
- Intersect roads, bridges, culverts, critical facilities, and candidate housing areas with flood zones and SLR/storm-surge polygons.
- Calculate exposed share:
  ```sql
  exposed_pct = ST_Area(ST_Intersection(unit.geom, hazard.geom)) / ST_Area(unit.geom)
  ```
- Classify exposure as none, low, moderate, high, avoid.

### Sea-Level-Rise And Storm-Surge Scenario Analysis

- Run multiple MGS scenarios separately.
- Compare current high tide, lower SLR scenario, mid scenario, and high planning scenario.
- Produce scenario delta maps showing which candidate sites drop out as risk tolerance tightens.

### Proximity Analysis

- Distance to roads, town centers, schools, hospitals, groceries, emergency services, transit stops, wastewater service areas, water lines, and employment centers.
- Use `ST_DWithin`, `ST_Distance`, QGIS distance matrix, or GeoPandas spatial joins.

### Network Accessibility

- Build a road network using MaineDOT roads or OSMnx.
- Calculate travel time to schools, hospitals, town halls, shelters, grocery stores, and employment centers.
- Use NetworkX shortest paths with speed assumptions from road class.

### Raster Reclassification

- Reclassify slope, elevation, land cover, imperviousness, and distance rasters to 0-100.
- Use Rasterio, GRASS `r.reclass`, QGIS raster calculator, or WhiteboxTools.

### Slope And Elevation Analysis

- Derive slope from USGS 3DEP DEM.
- Flag low-lying coastal terrain, depressions, and hydrologically connected lowlands.
- Use WhiteboxTools:
  ```bash
  whitebox_tools -r=Slope -v --wd=data/processed --dem=dem.tif --output=slope.tif
  ```

### Hotspot Analysis

- Use PySAL `esda` for Moran's I and Getis-Ord Gi* on tract/town vulnerability, housing need, and hazard overlap.
- Identify clusters of high need/high risk and high suitability/high need.

### Sensitivity Testing

- Re-run model with alternative weights.
- Compare rank stability using Spearman correlation and top-N overlap.
- Map locations that remain suitable across all scenarios as "robust opportunity zones."

## 10. Recommended Weighting Scheme

### Suitability Weights

| Indicator Group | Weight | Justification |
| --- | ---: | --- |
| Climate safety | 25% | Housing built today should remain safe through future flood and coastal-risk conditions. |
| Infrastructure efficiency | 20% | Maine towns need housing near existing roads, services, utilities, and centers to reduce public cost. |
| Environmental compatibility | 15% | Wetlands, conserved lands, shoreland areas, and habitats should not be treated as cheap vacant land. |
| Housing need alignment | 15% | Suitability should respond to actual housing pressure, not only land availability. |
| Social equity benefit | 10% | Safe housing opportunity should benefit vulnerable households and avoid worsening displacement. |
| Terrain and land-cover suitability | 10% | Slope, elevation, and land cover strongly affect build cost and environmental impact. |
| Local planning feasibility | 5% | Zoning and growth-area status matter, but data availability varies widely. |

### Vulnerability Weights

| Indicator Group | Weight | Justification |
| --- | ---: | --- |
| Social vulnerability | 25% | Income, age, disability, language, and tenure shape disaster impact and recovery. |
| Housing stress | 20% | Cost burden and unstable housing reduce resilience. |
| Climate exposure | 20% | Direct hazard exposure is the primary physical risk factor. |
| Infrastructure fragility | 15% | Roads, bridges, culverts, wastewater, and critical facilities determine access and recovery. |
| Mobility constraint | 10% | No-vehicle and long-distance households face evacuation and daily access barriers. |
| Recovery capacity gap | 10% | Broadband, income, age, disability, and service distance affect post-event recovery. |

Use stakeholder workshops to adjust weights for different policy scenarios. Do not hide the weights inside a black box.

## 11. Validation Strategy

1. **Historic flood comparison:** Compare flood exposure outputs against known flood damage reports, FEMA claims if available, high-water marks, municipal storm reports, and Maine Emergency Management Agency/local records.
2. **January 2024 coastal storm check:** Use documented coastal flooding and damage locations as a qualitative validation set for SLR/storm-surge exposure mapping.
3. **Planning document review:** Compare "avoid" and "suitable" zones with municipal comprehensive plans, climate action plans, shoreland zoning, hazard mitigation plans, and regional housing plans.
4. **Expert review:** Hold review sessions with municipal planners, regional planning organizations, MaineDOT, Maine Geological Survey, MaineHousing, conservation organizations, and emergency managers.
5. **Parcel spot checks:** Inspect top-ranked candidate parcels in QGIS using orthophotos, land cover, slope, wetlands, road access, and local zoning.
6. **Sensitivity analysis:** Validate that priority zones are not artifacts of one weight choice.
7. **Ground-truth limitations:** Label outputs as screening-grade; require site-level engineering, survey, wetland delineation, and legal zoning review before real development decisions.

## 12. Visualization Plan

### Static Maps For Publication

Use QGIS Layout Manager for:

- Statewide climate-safe housing suitability.
- Coastal SLR/storm-surge exposure.
- FEMA flood-risk avoidance areas.
- Environmental constraints.
- Infrastructure vulnerability.
- Social vulnerability/housing need.
- Priority resilience investment zones.
- Pilot-town parcel suitability maps.

### Interactive Web Maps

Use MapLibre GL JS for vector-tile maps from PostGIS/pg_tileserv:

- Toggle hazard scenarios.
- Filter by town, county, tract, or suitability class.
- Inspect candidate parcels/cells.
- Show policy scenario comparison.

Use Leaflet for a simpler public-facing map if vector tiles are not needed.

### Dashboards

Use Observable Framework, Streamlit, Dash, Panel, or Apache Superset:

- Town rankings.
- KPI cards.
- Scenario sliders.
- Scatterplots: housing need vs climate risk, suitability vs infrastructure access.
- Downloadable CSVs.

### Story Map-Style Presentation

Use Observable Framework, Quarto, or a static HTML narrative:

1. Maine housing need.
2. Climate and flood risk.
3. Land that should be avoided.
4. Where safe growth is most feasible.
5. Where resilience investment must come first.

### 3D/Elevation-Based Visualizations

Use QGIS 3D, Qgis2threejs, deck.gl TerrainLayer, or CesiumJS:

- Coastal elevation and SLR scenes.
- River corridor floodplain terrain.
- Candidate housing areas above hazard surfaces.
- Road/bridge exposure in low-elevation corridors.

## 13. Best Visualization Tools By Output

| Output | Recommended Tool | Why |
| --- | --- | --- |
| Publication-quality static maps | QGIS | Strong symbology, layout control, labels, atlas export, open-source cartography. |
| Interactive statewide suitability map | MapLibre GL JS + vector tiles | Fast rendering of many polygons/grid cells, open-source, modern web map styling. |
| Simple public viewer | Leaflet | Easier to maintain, good for smaller layers and public transparency. |
| Large point/grid exploration | deck.gl | Handles dense grid, hex, point, and 3D layers well. |
| Analyst dashboard | Observable Framework or Streamlit | Fast to build, strong charts, good narrative plus data exploration. |
| Enterprise-style dashboard | Apache Superset | Connects directly to PostGIS and supports repeatable filtering/charts. |
| 3D elevation/flood scenes | QGIS 3D, Qgis2threejs, CesiumJS, or deck.gl TerrainLayer | Makes elevation and inundation risk understandable to non-specialists. |
| Spatial services | pg_tileserv or GeoServer | Publishes PostGIS layers to web maps without proprietary GIS servers. |

## 14. Example Map Products

1. **Climate-Safe Housing Suitability Map**  
   Shows Tier 1, Tier 2, Tier 3, and Avoid areas. Include policy scenario toggle.

2. **Sea-Level-Rise And Storm-Surge Exposure Map**  
   Shows MGS inundation scenarios over parcels, roads, critical facilities, and town centers.

3. **Infrastructure Vulnerability Map**  
   Highlights roads, bridges, culverts, wastewater plants, and emergency facilities intersecting flood/SLR zones.

4. **Social Vulnerability And Housing Need Map**  
   Shows ACS/CDC SVI vulnerability, cost burden, no-vehicle households, older adults, disability, and renter pressure.

5. **Conservation And Environmental Constraint Map**  
   Shows wetlands, conserved land, shoreland zones, steep slopes, water bodies, and habitat constraints.

6. **Priority Investment Zones Map**  
   Identifies communities where housing need, social vulnerability, climate risk, and infrastructure fragility overlap.

7. **Scenario Sensitivity Map**  
   Shows areas that remain suitable under all weighting scenarios versus areas that are weight-sensitive.

## 15. Visual Design Guidance

- Use a calm neutral basemap; let hazards, suitability, and constraints carry the visual weight.
- Make `Avoid` areas dark red or muted charcoal, not bright decorative colors.
- Use blue only for water/flood/SLR, green for conservation/environment, orange for infrastructure exposure, purple or magenta sparingly for vulnerability.
- Do not map every layer at once. Build progressive views: risk, constraint, opportunity, priority.
- Use clear map titles written as questions, such as "Where can new housing avoid future coastal flooding?"
- Include uncertainty labels: "screening-grade," "requires local review," "parcel data incomplete," "scenario-based SLR."
- Put ranking tables beside maps for policymakers who need decisions, not only visuals.
- Use small-multiple scenario maps for SLR and weighting sensitivity.
- For public maps, show fewer categories: Safe Candidate, Conditional Candidate, Avoid, Existing Developed, Protected/Open Water.
- For technical maps, expose raw indicators and model scores.

## 16. Thesis Or Capstone Chapter Structure

1. Introduction: Maine housing need and climate-safe growth problem.
2. Literature and policy context: climate adaptation, suitability modeling, managed growth, vulnerability, Maine housing policy.
3. Study area: Maine geography, coastal/inland hazard context, housing markets, municipal planning structure.
4. Data and open-source tools.
5. Methods: exclusion mask, suitability model, vulnerability index, network and terrain analysis, sensitivity testing.
6. Results: statewide suitability, avoid-development zones, vulnerability clusters, priority investment zones, pilot-town parcel results.
7. Validation and uncertainty.
8. Visualization and decision-support products.
9. Policy implications for Maine municipalities and state agencies.
10. Conclusion and future work.

## 17. Twelve-Week Timeline

| Week | Work |
| --- | --- |
| 1 | Finalize research questions, study units, pilot towns, and policy scenarios. |
| 2 | Download and catalog Maine GeoLibrary, FEMA, MGS, ACS, MaineDOT, NWI, DEM, and conservation data. |
| 3 | Build PostGIS schema, load data, repair geometries, standardize CRS, document metadata. |
| 4 | Create flood/SLR exposure layers and hard exclusion mask. |
| 5 | Derive DEM products: elevation, slope, low-lying areas, hydrologic indicators. |
| 6 | Build infrastructure access metrics: road distance, network travel times, bridge/culvert exposure. |
| 7 | Build ACS housing need and social vulnerability index. |
| 8 | Create suitability model and baseline scenario. |
| 9 | Run alternative weighting scenarios and sensitivity testing. |
| 10 | Validate with flood events, planning documents, and expert/local review. |
| 11 | Build static maps, interactive map, dashboard, and story-map narrative. |
| 12 | Finalize report, thesis/capstone chapter, policy brief, and reproducible repository. |

## Today Sprint Plan

Because the goal is to finish a credible version today, use this same structure but reduce scope:

1. Use towns and census tracts as the primary units.
2. Use ACS housing/social indicators already in this project.
3. Add FEMA NFHL and MGS SLR/storm-surge layers for a coastal pilot, such as Cumberland and York Counties.
4. Use NWI wetlands and conservation lands as exclusions.
5. Use MaineDOT roads/bridges/culverts as infrastructure exposure and access proxies.
6. Use USGS 3DEP only for slope/elevation in pilot towns if statewide DEM download is too slow.
7. Produce three first outputs today:
   - `Climate-safe housing suitability pilot map`.
   - `Town/tract housing need and climate risk ranking`.
   - `Priority resilience investment zones`.

## 18. Limitations, Ethics, And Data Quality

- **Screening vs permitting:** Outputs cannot replace engineering studies, wetland delineation, legal zoning review, or local public process.
- **Parcel gaps:** Maine parcel data varies by municipality and may not be complete statewide.
- **Zoning inconsistency:** Municipal zoning data is not uniformly available or standardized.
- **Flood-map limits:** FEMA NFHL may not reflect future rainfall intensity, outdated hydrology, or unmapped local drainage problems.
- **SLR uncertainty:** MGS scenarios are planning surfaces, not precise predictions for individual structures.
- **Wetlands limits:** NWI is not a jurisdictional wetland delineation.
- **ACS uncertainty:** Small towns and tracts have margins of error; vulnerability rankings should include uncertainty or minimum-population flags.
- **Equity risk:** Suitability maps can accelerate speculation or displacement if released without affordability safeguards.
- **Tribal sovereignty:** Tribal lands and tribal data require respectful consultation and should not be treated as generic developable land.
- **Conservation ethics:** "Vacant" forest, farmland, or habitat is not automatically available or appropriate for development.
- **Managed retreat sensitivity:** Avoid-development recommendations can affect property values and should be communicated carefully.

## 19. Expected Results And Policy Implications

Expected results will likely show that Maine has three different planning problems:

1. **Coastal high-demand towns:** Strong housing need but substantial SLR, storm-surge, wetland, shoreland, and infrastructure exposure. Policy implication: focus on infill outside inundation zones, resilient redevelopment, conservation of high-risk land, and infrastructure hardening.
2. **Service-center towns:** More infrastructure-efficient housing potential near roads, jobs, schools, healthcare, and transit. Policy implication: prioritize affordable and mixed-income housing near existing centers, especially outside floodplains.
3. **Rural and aging communities:** High vulnerability, long commutes, older adults, disability, limited broadband, and infrastructure fragility. Policy implication: pair housing with broadband, healthcare access, senior mobility, road/culvert upgrades, and regional service hubs.

Policy deliverables can support:

- Municipal comprehensive plan updates.
- LD 2003 housing implementation.
- MaineHousing site screening.
- Regional housing production goals.
- Climate resilience grants.
- Culvert/bridge capital planning.
- Shoreland and floodplain ordinance updates.
- Conservation acquisition prioritization.
- Hazard mitigation plans.

## 20. Minimum Viable Project

**Goal:** Complete a defensible one-student version using QGIS, PostGIS, and Python.

**Study area:** Cumberland and York Counties, or a statewide town/tract model with a parcel pilot in 3-5 towns.

**Minimum datasets:**

- Census ACS 5-year housing/social indicators.
- Census tract/town boundaries.
- FEMA NFHL.
- MGS SLR/storm-surge layers for coastal areas.
- USFWS NWI wetlands.
- Maine conservation lands.
- MaineDOT roads, bridges, culverts.
- USGS 3DEP DEM or slope/elevation where feasible.
- MaineHousing housing production need study as policy framing.

**Minimum workflow:**

1. Load all vector layers into PostGIS.
2. Build hard exclusion mask: floodway, high-risk flood zones, SLR/storm surge, wetlands, conserved land, steep slope.
3. Create town/tract or parcel/grid candidate units.
4. Calculate exposure, infrastructure access, and vulnerability indicators.
5. Compute suitability and vulnerability scores with transparent weights.
6. Export ranked CSVs and GeoPackages.
7. Make five QGIS maps:
   - climate-safe housing suitability,
   - avoid-development constraints,
   - flood/SLR exposure,
   - social vulnerability and housing need,
   - priority investment zones.
8. Publish one interactive Leaflet or MapLibre map.
9. Write a concise policy brief for Maine municipalities.

**Minimum outputs today:**

- Research proposal and technical workflow.
- Data inventory.
- Suitability and vulnerability model.
- Initial PostGIS schema design.
- QGIS map specification.
- Dashboard/web map specification.
- Pilot implementation checklist.

## Source Links

- Maine GeoLibrary: https://mainegeolibrary-maine.hub.arcgis.com/
- Maine Geological Survey sea-level-rise/storm-surge data: https://www.maine.gov/DACF/mgs/hazards/slr_ss/index.shtml
- FEMA National Flood Hazard Layer: https://www.fema.gov/flood-maps/national-flood-hazard-layer
- USGS 3DEP: https://www.usgs.gov/3d-elevation-program
- U.S. Census ACS 5-year API: https://www.census.gov/data/developers/data-sets/acs-5year.html
- MaineDOT OpenData REST service: https://gis.maine.gov/mapservices/rest/services/dot/MaineDOT_OpenData/MapServer
- USFWS National Wetlands Inventory: https://www.fws.gov/program/national-wetlands-inventory/data-download
- CDC/ATSDR Social Vulnerability Index: https://www.atsdr.cdc.gov/place-health/php/svi/index.html
- Maine Bureau of Parks and Lands conservation GIS: https://www.maine.gov/dacf/parks/about/gis_mapping.shtml
- MaineHousing Housing Production Needs Study: https://www.mainehousing.org/docs/default-source/default-document-library/state-of-maine-housing-production-needs-study_full_final-v2.pdf
- USGS Annual NLCD: https://www.usgs.gov/annualNLCD
