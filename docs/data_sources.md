# Data Sources

This project prefers real public data and uses synthetic fallback layers only when a required layer is not yet available from the current catalog search.

## Live Sources

| Layer | Source | Endpoint |
| --- | --- | --- |
| Transit stops | GPCOG Greater Portland Transit Stop Inventory | `https://services3.arcgis.com/0UEH6aSHSRlnunGR/arcgis/rest/services/Greater_Portland_Transit_Stop_Inventory/FeatureServer/0` |
| Transit routes | GPCOG Greater Portland Transit Routes | `https://services3.arcgis.com/0UEH6aSHSRlnunGR/arcgis/rest/services/Greater_Portland_Transit_Routes/FeatureServer/34` |
| Sidewalks | GPCOG/PACTS Region Sidewalks | `https://services3.arcgis.com/0UEH6aSHSRlnunGR/arcgis/rest/services/PACTS_Region_Sidewalks/FeatureServer/0` |
| Study area | GPCOG/PACTS Study Area | `https://services3.arcgis.com/0UEH6aSHSRlnunGR/arcgis/rest/services/PACTS_Study_Area/FeatureServer/0` |

## Synthetic First-Run Layers

| Layer | Reason |
| --- | --- |
| Neighborhoods | A census block group source will be added in a later pass. Current synthetic polygons keep the analysis runnable. |
| Schools | A verified state/local school point source will be added later. |
| Hospitals | A verified healthcare facility source will be added later. |

Synthetic records are marked with `is_synthetic = true` in their destination tables.
