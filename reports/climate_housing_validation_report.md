# Climate Housing Technical Validation Report

This report is an automated technical quality gate for the current screening release. It does not replace validation against historic flood events, municipal plans, engineering studies, or expert/local review.

## Validation Summary

- Passed checks: **19**
- Failed checks: **0**
- Warning checks: **0**

| Check | Status | Detail |
| --- | --- | --- |
| Statewide town screen | **PASS** | 517 town records |
| Candidate grid coverage | **PASS** | 4,800 grid/town units |
| Hazard evidence loaded | **PASS** | 1,000 polygons |
| Environmental evidence loaded | **PASS** | 156 polygons |
| Infrastructure evidence loaded | **PASS** | 1,188 assets |
| Hazard geometry validity | **PASS** | 0 invalid geometries |
| Environmental geometry validity | **PASS** | 0 invalid geometries |
| Candidate geometry validity | **PASS** | 0 invalid geometries |
| Suitability score completeness | **PASS** | 0 null scores |
| Suitability score range | **PASS** | range 38.37 to 81.20; 0 outside 0-100 |
| Suitability tier completeness | **PASS** | 4,800 of 4,800 classified |
| Output: climate_housing_intelligence_app.html | **PASS** | 6,634,183 bytes |
| Output: climate_housing_candidate_grid.csv | **PASS** | 1,085,697 bytes |
| Output: climate_housing_candidate_grid.geojson | **PASS** | 5,456,889 bytes |
| Output: climate_housing_candidate_grid_report.html | **PASS** | 15,339 bytes |
| Output: climate_housing_candidate_grid_report.pdf | **PASS** | 280,902 bytes |
| Output: climate_housing_policy_decision_matrix.csv | **PASS** | 171,057 bytes |
| Output: climate_housing_policy_decision_matrix.pdf | **PASS** | 637,308 bytes |
| Output: climate_safe_housing_town_screening.geojson | **PASS** | 807,376 bytes |

## PostGIS Coverage Snapshot

| Dataset Role | Table | Records |
| --- | --- | --- |
| Candidate grid | `climate_housing_candidate_units` | 4,800 |
| Environmental constraints | `climate_housing_environmental_constraints` | 156 |
| Hazard polygons | `climate_housing_hazard_zones` | 1,000 |
| Infrastructure/exposed assets | `climate_housing_infrastructure_assets` | 1,188 |
| Town screening | `climate_housing_town_screening` | 517 |

## Remaining External Validation

- Compare flood-exposure flags with historic flood events, high-water marks, and local hazard-mitigation plans.
- Review high-scoring and avoid/review grid units with municipal planners, MaineHousing, Maine DEP, MaineDOT, and regional planning agencies.
- Load complete NWI wetlands, Maine Geological Survey sea-level-rise/storm-surge, DEM/slope, parcel, zoning, and water/wastewater capacity data before site-level claims.
- Run parcel-scale checks, field verification, and affordability/anti-displacement review before investment or permitting decisions.
