# Climate Housing Constraint Ingestion Summary

This audit records authoritative polygon overlays clipped to the Maine bounding box and loaded into PostGIS.

Feature cap per source: **1000**.

| Source | Model Role | Filter | Features Loaded | URL |
| --- | --- | --- | --- | --- |
| FEMA National Flood Hazard Layer | hazard: flood | `SFHA_TF='T' OR ZONE_SUBTY='0.2 PCT ANNUAL CHANCE FLOOD HAZARD'` | 1000 | https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28 |
| Maine GeoLibrary Conserved Lands | environment: conserved_land | `1=1` | 156 | https://services5.arcgis.com/8TufBwUCMF4Azg37/arcgis/rest/services/Maine_Conserved_Lands/FeatureServer/16 |
| U.S. Fish and Wildlife Service National Wetlands Inventory | environment: wetland | `1=1` | 0 | https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/Wetlands/MapServer/0 |

## Source Errors

- **nwi_wetlands:** TimeoutError: The read operation timed out

## Interpretation

- FEMA polygons include Special Flood Hazard Areas and mapped 0.2 percent annual-chance flood hazard areas.
- Conserved land and NWI wetland polygons are treated as environmental screening constraints, not automatic legal determinations.
- The candidate-grid model measures polygon overlap as a share of each grid/town intersection.
- A feature cap makes this a bounded reproducible screening run. Remove `--max-features` for complete source ingestion when runtime and storage allow.
- Parcel boundaries, local zoning, shoreland zoning, municipal water/wastewater capacity, and DEM-derived slope remain required before site selection or permitting decisions.
