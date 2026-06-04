# Climate Housing Town Boundary Summary

- Boundary source: U.S. Census TIGER/Line 2024 Maine county subdivisions.
- Source URL: `https://www2.census.gov/geo/tiger/TIGER2024/COUSUB/tl_2024_23_cousub.zip`.
- Raw cache: `C:\Users\radah\Qgis_demo\data\raw\tl_2024_23_cousub.zip`.
- Boundaries loaded to PostGIS: **529**.
- Scored populated places exported to GeoJSON: **518**.
- Map-ready screening GeoJSON: `C:\Users\radah\Qgis_demo\reports\climate_safe_housing_town_screening.geojson`.

## What This Enables

- QGIS can now map town-level climate-safe housing MVP scores as polygons.
- Web maps can load `reports/climate_safe_housing_town_screening.geojson` directly.
- Climate/infrastructure asset sample counts can be spatially joined to towns.
- The next step is adding full hazard and constraint polygons, then calculating true exposure shares by town, tract, parcel, or grid cell.
