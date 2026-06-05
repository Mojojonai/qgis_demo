# Data Sources

This project prefers real public data and uses synthetic fallback layers only when a required layer is not yet available from the current catalog search.

## Live Sources

| Layer | Source | Endpoint |
| --- | --- | --- |
| Transit stops | GPCOG Greater Portland Transit Stop Inventory | `https://services3.arcgis.com/0UEH6aSHSRlnunGR/arcgis/rest/services/Greater_Portland_Transit_Stop_Inventory/FeatureServer/0` |
| Transit routes | GPCOG Greater Portland Transit Routes | `https://services3.arcgis.com/0UEH6aSHSRlnunGR/arcgis/rest/services/Greater_Portland_Transit_Routes/FeatureServer/34` |
| Sidewalks | GPCOG/PACTS Region Sidewalks | `https://services3.arcgis.com/0UEH6aSHSRlnunGR/arcgis/rest/services/PACTS_Region_Sidewalks/FeatureServer/0` |
| Study area | GPCOG/PACTS Study Area | `https://services3.arcgis.com/0UEH6aSHSRlnunGR/arcgis/rest/services/PACTS_Study_Area/FeatureServer/0` |
| ACS town demographics | U.S. Census Bureau ACS 2024 5-year table-based Summary File | `https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/` |
| FEMA flood hazard polygons | FEMA National Flood Hazard Layer | `https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28` |
| Conserved lands | Maine GeoLibrary Conserved Lands | `https://services5.arcgis.com/8TufBwUCMF4Azg37/arcgis/rest/services/Maine_Conserved_Lands/FeatureServer/16` |
| Wetlands | U.S. Fish and Wildlife Service National Wetlands Inventory | `https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/Wetlands/MapServer/0` |
| Bridges and cross culverts | MaineDOT OpenData | `https://gis.maine.gov/mapservices/rest/services/dot/MaineDOT_OpenData/MapServer` |
| Regulated sites exposed to flood/sea-level-rise scenarios | Maine DEP Sea Level Rise Study | `https://gis.maine.gov/mapservices/rest/services/dep/MaineDEPSeaLevelRiseStudy/MapServer` |

The ACS loader streams official Summary File tables for Maine county subdivisions and caches town records in `data/raw/acs_town_demographics.json`. Current indicators include total population, median household income, poverty, zero-vehicle households, population age 65 and older, disability, children under 18, housing cost burden, vacancy/seasonal housing pressure, commute mode, long-commute pressure, work-from-home, and household internet access. The statewide future-livability and government-priority reports score all populated Maine towns and cities from these ACS indicators, while the detailed transit/QGIS analysis still uses the Greater Portland spatial layers listed above.

The climate-housing constraint loader clips public polygon services to Maine and records every run in `reports/climate_housing_constraint_ingestion_summary.md`. The current bounded run includes FEMA flood polygons and the complete queryable conserved-land service. The NWI public MapServer is timing out during geometry queries; the official Maine state GeoPackage is approximately 417 MB and remains the recommended complete wetland-ingestion path for a production deployment.

## Synthetic First-Run Layers

| Layer | Reason |
| --- | --- |
| Neighborhoods | A census block group source will be added in a later pass. Current synthetic polygons keep the analysis runnable. |
| Schools | A verified state/local school point source will be added later. |
| Hospitals | A verified healthcare facility source will be added later. |

Synthetic records are marked with `is_synthetic = true` in their destination tables.
