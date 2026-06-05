# Climate-Safe Housing Research Completion Audit

## Release Status

The same-day release now provides a reproducible statewide planning screen, a 5 km candidate-grid suitability model, synchronized interactive exploration, policy-action classifications, source-ingestion audits, and an automated technical validation report.

It is ready to answer statewide screening questions such as:

- Which towns combine housing need, social vulnerability, and infrastructure pressure?
- Which grid areas should move first into parcel-level review?
- Which grid areas show enough flood or environmental evidence to require avoidance or detailed review?
- Where should housing work be paired with resilience and anti-displacement investment?

It is not a parcel-level build/no-build or permitting system.

## Twelve-Week Plan Status

| Week | Planned Work | Current Status | Evidence |
| --- | --- | --- | --- |
| 1 | Research questions, units, pilot towns, scenarios | Complete | Research proposal, statewide town unit, 5 km grid unit, scenario modes |
| 2 | Download and catalog authoritative data | Partially complete | ACS, FEMA sample, conserved lands, MaineDOT, Maine DEP, source audits; complete NWI/MGS/DEM/parcels/zoning still required |
| 3 | PostGIS schema, geometry repair, CRS, metadata | Complete for current sources | Climate-housing schema, geometry cleaning, raw properties, spatial indexes |
| 4 | Flood/SLR exposure and exclusion mask | Planning-grade complete | FEMA/DEP evidence, overlap-area scoring, avoid/detailed-review tier; complete MGS and FEMA coverage still required |
| 5 | DEM elevation, slope, hydrology | Deferred precision layer | USGS 3DEP/terrain workflow remains external work |
| 6 | Infrastructure access and exposure | Planning-grade complete | MaineDOT bridges/culverts, DEP exposed sites, town infrastructure proxy; network and utility capacity remain external work |
| 7 | Housing need and social vulnerability | Complete | ACS-backed town screening for 517 Maine towns/cities |
| 8 | Baseline suitability model | Complete | PostGIS statewide 5 km candidate-grid model |
| 9 | Alternative scenarios and sensitivity | Complete for screening | Scenario modes and transparent weighted scoring in synchronized app |
| 10 | Validation | Technical validation complete | Automated geometry, coverage, score, classification, and output checks; expert/event validation remains external |
| 11 | Maps, dashboard, narrative | Complete for web/report release | Synchronized intelligence app, interactive map, PDFs, CSVs, GeoJSONs, policy reports |
| 12 | Final report, policy brief, reproducible repository | Complete for current scope | Proposal, reports, scripts, SQL, README, source documentation, validation audit |

## Current Release Evidence

- 517 Maine town/city screening records.
- 4,800 statewide grid/town candidate units.
- 1,000 FEMA flood hazard polygons in the bounded release.
- 156 Maine conserved-land polygons from the queryable service.
- 1,188 infrastructure and climate-exposed assets.
- 19 automated validation checks passed, with no failed checks.

## Precision Layers Required Before Site-Level Decisions

1. Complete FEMA NFHL and NWI wetlands coverage.
2. Maine Geological Survey sea-level-rise and storm-surge polygons.
3. USGS 3DEP elevation, slope, and hydrologic indicators.
4. Parcel boundaries, local zoning, shoreland zoning, and ownership constraints.
5. Municipal water, wastewater, road, school, emergency-service, and broadband capacity.
6. Historic flood-event comparison and review by municipalities, agencies, and affected communities.

## Decision Guardrail

Use the outputs to prioritize where detailed review should begin and where resilience investment is urgent. Do not describe a grid cell as build-ready without parcel-scale environmental, engineering, zoning, infrastructure, affordability, and public-process review.
