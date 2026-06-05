# Climate-Safe Housing Candidate Grid Model

## What This Adds

This model converts Maine town screening results into statewide 5 km planning grid units. Each grid cell inherits town-level housing need, social vulnerability, and infrastructure proxy scores, then adds exposure signals from loaded hazard zones, environmental constraints, and nearby climate/infrastructure assets.

The result is a first grid-level suitability screen. It is more spatially explicit than town rankings, but it is not a parcel suitability determination. This build includes bounded FEMA NFHL polygons, the queryable Maine conserved-land service, and climate/infrastructure assets. Complete FEMA and NWI coverage, Maine Geological Survey inundation, DEM/slope, zoning, water/wastewater, and parcels are still required before final build/no-build decisions.

## Model Formula

| Component | Weight | Meaning |
| --- | --- | --- |
| Housing need | 30% | Prioritizes places where housing pressure is visible. |
| Infrastructure access proxy | 30% | Rewards locations in towns with stronger service/access indicators and nearby road structures. |
| Low flood exposure | 20% | Penalizes loaded flood/SLR hazard and exposed-asset signals. |
| Low environmental constraint | 10% | Penalizes loaded wetland/conservation/environmental constraint intersections. |
| Lower social vulnerability | 10% | Avoids treating highly vulnerable communities as simple growth targets without safeguards. |

## Output Snapshot

| KPI | Value |
| --- | --- |
| Candidate grid units in PostGIS | 4,800 |
| Grid units exported to GeoJSON | 4,800 |
| Strong candidate units | 173 |
| Moderate candidate units | 3,877 |
| Avoid or detailed hazard review units | 42 |
| Resilience-before-growth units | 0 |
| Loaded hazard polygons | 1,000 |
| Loaded environmental constraints | 156 |
| Loaded infrastructure/exposed assets | 1,188 |

## Loaded Spatial Evidence

| Role | Source | Features In PostGIS |
| --- | --- | --- |
| environmental constraint | Maine GeoLibrary Conserved Lands | 156 |
| hazard polygon | FEMA National Flood Hazard Layer | 1,000 |
| infrastructure/exposed asset | Maine DEP Sea Level Rise Study | 688 |
| infrastructure/exposed asset | MaineDOT OpenData - Bridges | 250 |
| infrastructure/exposed asset | MaineDOT OpenData - Cross Culverts | 250 |

## Suitability Tier Counts

| Tier | Grid Units |
| --- | --- |
| moderate candidate for parcel screening | 3,877 |
| monitor after full overlays | 708 |
| strong candidate for parcel screening | 173 |
| avoid or detailed hazard review | 42 |

## Highest Scoring Candidate Grid Units

| Grid Unit | Town | County | Score | Tier | Flood | Env | Infra | Housing | Vulnerability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grid5km_2300560545_2478 | Portland | Cumberland | 81.20 | strong candidate for parcel screening | 0.00 | 0.00 | 84.36 | 67.34 | 43.12 |
| grid5km_2300560545_2372 | Portland | Cumberland | 81.20 | strong candidate for parcel screening | 0.00 | 0.00 | 84.36 | 67.34 | 43.12 |
| grid5km_2300560545_2587 | Portland | Cumberland | 81.20 | strong candidate for parcel screening | 0.00 | 0.00 | 84.36 | 67.34 | 43.12 |
| grid5km_2300560545_2481 | Portland | Cumberland | 81.20 | strong candidate for parcel screening | 0.00 | 0.00 | 84.36 | 67.34 | 43.12 |
| grid5km_2300560545_2479 | Portland | Cumberland | 81.20 | strong candidate for parcel screening | 0.00 | 0.00 | 84.36 | 67.34 | 43.12 |
| grid5km_2300560545_2693 | Portland | Cumberland | 81.20 | strong candidate for parcel screening | 0.00 | 0.00 | 84.36 | 67.34 | 43.12 |
| grid5km_2300560545_2480 | Portland | Cumberland | 81.20 | strong candidate for parcel screening | 0.00 | 0.00 | 84.36 | 67.34 | 43.12 |
| grid5km_2300560545_2586 | Portland | Cumberland | 81.20 | strong candidate for parcel screening | 0.00 | 0.00 | 84.36 | 67.34 | 43.12 |
| grid5km_2300560545_2053 | Portland | Cumberland | 81.20 | strong candidate for parcel screening | 0.00 | 0.00 | 84.36 | 67.34 | 43.12 |
| grid5km_2300560545_2371 | Portland | Cumberland | 81.20 | strong candidate for parcel screening | 0.00 | 0.00 | 84.36 | 67.34 | 43.12 |
| grid5km_2300560545_2373 | Portland | Cumberland | 81.20 | strong candidate for parcel screening | 0.00 | 0.00 | 84.36 | 67.34 | 43.12 |
| grid5km_2300560545_2374 | Portland | Cumberland | 78.60 | strong candidate for parcel screening | 16.00 | 0.00 | 86.36 | 67.34 | 43.12 |
| grid5km_2300138740_2168 | Lewiston | Androscoggin | 75.32 | strong candidate for parcel screening | 0.00 | 0.00 | 66.55 | 70.39 | 57.61 |
| grid5km_2300138740_2061 | Lewiston | Androscoggin | 74.96 | strong candidate for parcel screening | 4.78 | 0.00 | 68.55 | 70.39 | 57.61 |
| grid5km_2300138740_1955 | Lewiston | Androscoggin | 74.16 | strong candidate for parcel screening | 8.78 | 0.00 | 68.55 | 70.39 | 57.61 |
| grid5km_2300330690_3741 | Hamlin | Aroostook | 73.94 | strong candidate for parcel screening | 0.00 | 0.00 | 63.96 | 70.50 | 64.00 |
| grid5km_2300138740_2167 | Lewiston | Androscoggin | 73.40 | strong candidate for parcel screening | 3.62 | 0.00 | 62.55 | 70.39 | 57.61 |
| grid5km_2300138740_2060 | Lewiston | Androscoggin | 73.33 | strong candidate for parcel screening | 6.97 | 0.00 | 64.55 | 70.39 | 57.61 |
| grid5km_2300138740_2062 | Lewiston | Androscoggin | 73.29 | strong candidate for parcel screening | 10.14 | 0.00 | 66.55 | 70.39 | 57.61 |
| grid5km_2301902795_3796 | Bangor | Penobscot | 72.97 | strong candidate for parcel screening | 0.00 | 0.00 | 61.89 | 66.36 | 55.07 |

## Grid Units Requiring Avoidance Or Detailed Hazard Review

| Grid Unit | Town | County | Score | Tier | Flood | Env | Infra | Housing | Vulnerability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grid5km_2300560545_2266 | Portland | Cumberland | 65.80 | avoid or detailed hazard review | 80.00 | 0.00 | 86.36 | 67.34 | 43.12 |
| grid5km_2300560545_2265 | Portland | Cumberland | 65.20 | avoid or detailed hazard review | 80.00 | 0.00 | 84.36 | 67.34 | 43.12 |
| grid5km_2300560545_2051 | Portland | Cumberland | 63.20 | avoid or detailed hazard review | 96.00 | 0.00 | 88.36 | 67.34 | 43.12 |
| grid5km_2300560545_2158 | Portland | Cumberland | 62.40 | avoid or detailed hazard review | 100.00 | 0.00 | 88.36 | 67.34 | 43.12 |
| grid5km_2300560545_2159 | Portland | Cumberland | 62.40 | avoid or detailed hazard review | 100.00 | 0.00 | 88.36 | 67.34 | 43.12 |
| grid5km_2300560545_2052 | Portland | Cumberland | 62.40 | avoid or detailed hazard review | 100.00 | 0.00 | 88.36 | 67.34 | 43.12 |
| grid5km_2300571990_2158 | South Portland | Cumberland | 54.13 | avoid or detailed hazard review | 100.00 | 0.00 | 69.01 | 56.97 | 36.60 |
| grid5km_2301902795_3901 | Bangor | Penobscot | 53.77 | avoid or detailed hazard review | 96.00 | 0.00 | 61.89 | 66.36 | 55.07 |
| grid5km_2300571990_2265 | South Portland | Cumberland | 53.73 | avoid or detailed hazard review | 96.00 | 0.00 | 65.01 | 56.97 | 36.60 |
| grid5km_2300571990_2051 | South Portland | Cumberland | 53.53 | avoid or detailed hazard review | 100.00 | 0.00 | 67.01 | 56.97 | 36.60 |
| grid5km_2301506120_3021 | Boothbay Harbor | Lincoln | 53.27 | avoid or detailed hazard review | 80.00 | 0.00 | 44.29 | 73.17 | 59.66 |
| grid5km_2301363660_3780 | Rockport | Knox | 53.20 | avoid or detailed hazard review | 88.00 | 0.00 | 53.33 | 59.63 | 30.88 |
| grid5km_2301363590_3778 | Rockland | Knox | 50.82 | avoid or detailed hazard review | 100.00 | 0.00 | 58.49 | 59.93 | 47.11 |
| grid5km_2301186515_2608 | Winslow | Kennebec | 50.55 | avoid or detailed hazard review | 80.00 | 0.00 | 47.58 | 54.58 | 41.03 |
| grid5km_2300582105_1945 | Westbrook | Cumberland | 50.38 | avoid or detailed hazard review | 100.00 | 0.00 | 61.29 | 51.15 | 33.55 |
| grid5km_2300582105_2052 | Westbrook | Cumberland | 50.38 | avoid or detailed hazard review | 100.00 | 0.00 | 61.29 | 51.15 | 33.55 |
| grid5km_2303164675_1940 | Saco | York | 50.37 | avoid or detailed hazard review | 100.00 | 0.00 | 58.81 | 53.19 | 32.27 |
| grid5km_2300972865_4962 | Southwest Harbor | Hancock | 50.29 | avoid or detailed hazard review | 100.00 | 0.00 | 45.18 | 70.39 | 43.84 |
| grid5km_2301102100_2496 | Augusta | Kennebec | 50.18 | avoid or detailed hazard review | 100.00 | 0.00 | 54.05 | 65.03 | 55.44 |
| grid5km_2301309725_3780 | Camden | Knox | 49.49 | avoid or detailed hazard review | 96.00 | 0.00 | 53.28 | 56.19 | 41.54 |

## Resilience-Before-Growth Grid Units

| Grid Unit | Town | County | Score | Tier | Flood | Env | Infra | Housing | Vulnerability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## County Portfolio Summary

| County | Grid Units | Avg Score | Strong Candidates | Hazard Review |
| --- | --- | --- | --- | --- |
| Cumberland | 297 | 65.74 | 33 | 11 |
| York | 306 | 64.32 | 26 | 3 |
| Hancock | 421 | 64.32 | 24 | 4 |
| Androscoggin | 127 | 63.51 | 19 | 1 |
| Aroostook | 628 | 61.95 | 19 | 1 |
| Penobscot | 526 | 61.96 | 17 | 2 |
| Knox | 227 | 63.97 | 15 | 9 |
| Kennebec | 236 | 64.11 | 11 | 2 |
| Franklin | 219 | 61.57 | 9 | 0 |
| Sagadahoc | 94 | 63.33 | 0 | 2 |
| Waldo | 228 | 63.01 | 0 | 0 |
| Washington | 443 | 62.26 | 0 | 3 |
| Oxford | 357 | 62.09 | 0 | 0 |
| Lincoln | 179 | 62.04 | 0 | 4 |
| Somerset | 325 | 60.62 | 0 | 0 |
| Piscataquis | 187 | 60.61 | 0 | 0 |

## How To Use This Output

- Use strong and moderate candidate grid units to choose where parcel screening should start.

- Use avoid/review units as a warning layer, not as a final legal restriction.

- Use resilience-before-growth units to prioritize infrastructure, anti-displacement, emergency access, and recovery-capacity investment.

- Use the GeoJSON in QGIS or the web app as a planning overlay with the existing town-screening outputs.

## Next Precision Step

Replace the 5 km grid with parcel or 250 m grid cells in pilot towns after full hazard, wetlands, conservation, DEM/slope, zoning, roads, bridges, culverts, water/wastewater, and parcel layers are loaded.