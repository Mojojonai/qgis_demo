# Climate-Safe Housing Growth Areas MVP Screening

## What This Is

This is the same-day MVP for the Maine climate-safe housing research project. It ranks Maine towns using statewide ACS housing, vulnerability, commute, digital-access, and seasonal-housing indicators already loaded in PostGIS.

It does **not** yet claim that any parcel is climate-safe. FEMA flood zones, Maine Geological Survey sea-level-rise/storm-surge scenarios, wetlands, conserved land, slope, roads, bridges, culverts, parcels, and zoning still need to be spatially overlaid before parcel-level recommendations are made.

## What It Answers Today

- Maine populated towns/county subdivisions screened: **518**.
- Highest MVP climate-safe housing search priority: **Portland**, Cumberland County.
- Highest resilience investment priority: **Bancroft UT**, Aroostook County.
- Highest housing pressure signal: **Allagash**, Aroostook County.
- Strongest infrastructure-efficiency proxy: **Portland**, Cumberland County.

## MVP Scoring Logic

| Score | Inputs | Purpose |
| --- | --- | --- |
| Housing need | cost burden, renter burden, poverty, seasonal housing, zero-car households, population scale | Find towns where housing production or year-round affordability pressure is high. |
| Social vulnerability | poverty, older adults, disability, zero-car households, digital gap, cost burden | Find towns where climate disruption and housing instability could hurt people most. |
| Infrastructure-efficiency proxy | population scale, commute efficiency, digital capacity, work-from-home, income, year-round housing capacity | Identify towns that may support efficient growth before detailed road/utility overlays. |
| Resilience investment priority | social vulnerability, housing need, long commutes, digital gap, seasonal pressure | Find places where public investment should come before or alongside housing growth. |
| MVP climate-safe housing search priority | housing need, infrastructure proxy, vulnerability, population scale, year-round capacity | Rank where to run the next parcel-level FEMA/MGS/wetlands/roads overlay first. |

## Top MVP Climate-Safe Housing Search Priorities

| Rank | Town | County | Score | Population | Cost Burden | Seasonal Housing | Long Commute | Key Drivers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Portland | Cumberland | 73.04 | 68,854 | 41.49% | 5.16% | 6.59% | renter cost burden; housing cost burden; zero-car households; children/family demand |
| 2 | Lewiston | Androscoggin | 66.36 | 38,324 | 40.71% | 0.58% | 11.19% | renter cost burden; housing cost burden; poverty; zero-car households |
| 3 | Bangor | Penobscot | 63.32 | 31,938 | 39.56% | 0.21% | 7.1% | renter cost burden; housing cost burden; poverty; disability |
| 4 | Waterville | Kennebec | 60.04 | 17,077 | 38.81% | 0.26% | 5.78% | renter cost burden; poverty; housing cost burden; zero-car households |
| 5 | Orono | Penobscot | 58.4 | 11,902 | 46.29% | 1.43% | 3.56% | renter cost burden; poverty; housing cost burden; disability |
| 6 | Augusta | Kennebec | 58.19 | 19,077 | 38.81% | 1.51% | 9.1% | renter cost burden; housing cost burden; poverty; disability |
| 7 | Auburn | Androscoggin | 57.53 | 24,602 | 42.58% | 0.99% | 13.3% | renter cost burden; housing cost burden; children/family demand; disability |
| 8 | South Portland | Cumberland | 56.66 | 26,930 | 43.29% | 0.81% | 3.52% | renter cost burden; housing cost burden; children/family demand; older adults |
| 9 | Old Town | Penobscot | 55.97 | 7,470 | 41.56% | 1.44% | 4.71% | renter cost burden; poverty; housing cost burden; children/family demand |
| 10 | Eustis | Franklin | 55.53 | 453 | 51.25% | 61.53% | 0% | housing cost burden; renter cost burden; seasonal housing pressure; poverty |
| 11 | Machias | Washington | 55.47 | 2,020 | 43.85% | 0.71% | 9.98% | renter cost burden; poverty; housing cost burden; disability |
| 12 | Van Buren | Aroostook | 55.01 | 1,858 | 39.64% | 2.89% | 9.26% | disability; poverty; renter cost burden; housing cost burden |
| 13 | Grand Isle | Aroostook | 54.43 | 407 | 42.57% | 3.92% | 2.4% | renter cost burden; housing cost burden; poverty; disability |
| 14 | Hamlin | Aroostook | 54.39 | 111 | 52.63% | 11.76% | 4% | housing cost burden; renter cost burden; disability; older adults |
| 15 | Dexter | Penobscot | 54.07 | 3,822 | 35.71% | 3.35% | 12.38% | renter cost burden; poverty; disability; housing cost burden |
| 16 | Madawaska | Aroostook | 53.57 | 3,853 | 43.77% | 13.91% | 0% | renter cost burden; housing cost burden; zero-car households; disability |
| 17 | Rumford | Oxford | 53.45 | 5,942 | 38.03% | 7.92% | 14.67% | renter cost burden; poverty; housing cost burden; disability |
| 18 | Caribou | Aroostook | 52.94 | 7,382 | 38.58% | 1.17% | 4.31% | renter cost burden; housing cost burden; poverty; disability |
| 19 | Brunswick | Cumberland | 52.85 | 22,336 | 39.32% | 1.73% | 10.74% | renter cost burden; housing cost burden; children/family demand; older adults |
| 20 | Presque Isle | Aroostook | 52.69 | 8,736 | 37.44% | 0.43% | 3.19% | renter cost burden; housing cost burden; poverty; disability |
| 21 | Biddeford | York | 52.64 | 22,498 | 34.82% | 6.81% | 9.85% | renter cost burden; housing cost burden; poverty; children/family demand |
| 22 | Rockland | Knox | 52.49 | 7,035 | 41.31% | 3.55% | 1.84% | renter cost burden; housing cost burden; disability; older adults |
| 23 | Westbrook | Cumberland | 52.09 | 20,775 | 37.02% | 0.52% | 3.74% | renter cost burden; housing cost burden; children/family demand; disability |
| 24 | Belfast | Waldo | 52.07 | 6,986 | 35.88% | 9.51% | 13.01% | renter cost burden; older adults; housing cost burden; zero-car households |
| 25 | North Washington UT | Washington | 52.06 | 620 | 46.26% | 60.06% | 4.57% | renter cost burden; poverty; seasonal housing pressure; disability |
| 26 | East Millinocket | Penobscot | 51.91 | 1,495 | 34.31% | 5.87% | 8.17% | renter cost burden; poverty; disability; housing cost burden |
| 27 | Houlton | Aroostook | 51.6 | 6,056 | 32.44% | 2.35% | 2.49% | renter cost burden; poverty; housing cost burden; disability |
| 28 | Brewer | Penobscot | 51.5 | 9,652 | 37.57% | 1.43% | 7.74% | renter cost burden; housing cost burden; children/family demand; disability |
| 29 | Skowhegan | Somerset | 51.32 | 8,653 | 40.23% | 2.7% | 16.18% | renter cost burden; housing cost burden; disability; children/family demand |
| 30 | Alton | Penobscot | 51.21 | 819 | 29.25% | 1.63% | 4.47% | renter cost burden; poverty; housing cost burden; children/family demand |
| 31 | Patten | Penobscot | 51.19 | 1,154 | 30.9% | 8.63% | 18.09% | renter cost burden; poverty; disability; older adults |
| 32 | West Paris | Oxford | 51.14 | 1,808 | 40% | 15.91% | 23.19% | renter cost burden; poverty; housing cost burden; long commutes |
| 33 | Saco | York | 50.97 | 20,819 | 37.47% | 4.25% | 7.06% | renter cost burden; housing cost burden; children/family demand; disability |
| 34 | Scarborough | Cumberland | 50.86 | 23,215 | 35.42% | 7.69% | 4.55% | renter cost burden; housing cost burden; children/family demand; older adults |
| 35 | Sanford | York | 50.58 | 22,247 | 35.3% | 2.41% | 19.18% | renter cost burden; housing cost burden; disability; children/family demand |

## Top Resilience Investment Priorities

| Rank | Town | County | Score | Population | Cost Burden | Seasonal Housing | Long Commute | Key Drivers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Bancroft UT | Aroostook | 85.82 | 78 | 33.33% | 40.22% | 100% | poverty; older adults; seasonal housing pressure; long commutes |
| 2 | Allagash | Aroostook | 72.52 | 224 | 54.76% | 34.46% | 31.25% | housing cost burden; renter cost burden; poverty; seasonal housing pressure |
| 3 | Brighton | Somerset | 69.46 | 98 | 71.43% | 62.35% | 35.29% | housing cost burden; renter cost burden; poverty; seasonal housing pressure |
| 4 | St. Albans | Somerset | 66.11 | 1,831 | 31.77% | 25.83% | 34.03% | renter cost burden; long commutes; poverty; disability |
| 5 | The Forks | Somerset | 64.94 | 92 | 7.5% | 76.44% | 27.63% | seasonal housing pressure; poverty; long commutes; older adults |
| 6 | Danforth | Washington | 62.15 | 666 | 32.5% | 42.07% | 32.37% | disability; seasonal housing pressure; long commutes; renter cost burden |
| 7 | Kingman UT | Penobscot | 62.15 | 138 | 24.36% | 37.1% | 26.67% | renter cost burden; poverty; seasonal housing pressure; long commutes |
| 8 | Osborn | Hancock | 60.83 | 88 | 44.9% | 45.45% | 50% | renter cost burden; seasonal housing pressure; long commutes; housing cost burden |
| 9 | Macwahoc | Aroostook | 60.56 | 79 | 22.64% | 28.87% | 70% | poverty; older adults; disability; long commutes |
| 10 | Blanchard UT | Piscataquis | 60.33 | 81 | 33.33% | 42.4% | 66.67% | renter cost burden; older adults; seasonal housing pressure; long commutes |
| 11 | North Washington UT | Washington | 59.68 | 620 | 46.26% | 60.06% | 4.57% | renter cost burden; poverty; seasonal housing pressure; disability |
| 12 | Haynesville | Aroostook | 59.64 | 131 | 46.77% | 35.09% | 27.54% | renter cost burden; seasonal housing pressure; housing cost burden; long commutes |
| 13 | Hersey | Aroostook | 59.42 | 47 | 16.67% | 34.69% | 29.41% | seasonal housing pressure; disability; long commutes; poverty |
| 14 | Avon | Franklin | 59.3 | 359 | 42.75% | 44.31% | 27.63% | renter cost burden; seasonal housing pressure; housing cost burden; long commutes |
| 15 | Burlington | Penobscot | 59.27 | 328 | 20.45% | 47% | 46.84% | disability; seasonal housing pressure; long commutes; poverty |
| 16 | Lee | Penobscot | 59.2 | 925 | 33.67% | 35% | 24.43% | renter cost burden; seasonal housing pressure; poverty; long commutes |
| 17 | Crawford | Washington | 59.15 | 97 | 22% | 46.76% | 11.11% | renter cost burden; poverty; older adults; disability |
| 18 | Carroll | Penobscot | 58.74 | 134 | 35.29% | 38.46% | 42.31% | seasonal housing pressure; long commutes; poverty; housing cost burden |
| 19 | Cherryfield | Washington | 58.47 | 809 | 32.9% | 15.82% | 24.91% | renter cost burden; poverty; disability; long commutes |
| 20 | Winn | Penobscot | 58.34 | 287 | 45.27% | 4.95% | 49.57% | renter cost burden; long commutes; disability; housing cost burden |
| 21 | Bridgton | Cumberland | 57.79 | 5,642 | 30.92% | 47.71% | 39.25% | seasonal housing pressure; long commutes; disability; housing cost burden |
| 22 | Mount Chase | Penobscot | 57.67 | 280 | 37.39% | 53.71% | 16.67% | poverty; seasonal housing pressure; housing cost burden; disability |
| 23 | Great Pond | Hancock | 57.62 | 42 | 22.22% | 42.86% | 45.45% | renter cost burden; older adults; seasonal housing pressure; long commutes |
| 24 | Wesley | Washington | 57.59 | 320 | 12.69% | 34.5% | 31.21% | poverty; seasonal housing pressure; long commutes; disability |
| 25 | Kingsbury | Piscataquis | 57.55 | 17 | 0% | 85.44% | 33.33% | poverty; older adults; disability; seasonal housing pressure |
| 26 | Pleasant Ridge | Somerset | 57.33 | 87 | 17.24% | 48.78% | 27.27% | older adults; disability; seasonal housing pressure; long commutes |
| 27 | Moscow | Somerset | 57.2 | 865 | 25.5% | 19.65% | 31.99% | long commutes; renter cost burden; poverty; seasonal housing pressure |
| 28 | Sumner | Oxford | 57.13 | 845 | 41.98% | 34.05% | 35.22% | renter cost burden; seasonal housing pressure; long commutes; housing cost burden |
| 29 | Lincoln | Oxford | 57.12 | 47 | 15% | 81.29% | 28.57% | seasonal housing pressure; disability; long commutes; older adults |
| 30 | Newfield | York | 56.75 | 1,580 | 26.21% | 34.19% | 45.63% | seasonal housing pressure; long commutes; renter cost burden; disability |
| 31 | New Vineyard | Franklin | 56.6 | 607 | 33.64% | 39.41% | 20.61% | renter cost burden; seasonal housing pressure; poverty; children/family demand |
| 32 | Prentiss UT | Penobscot | 56.5 | 210 | 17.53% | 33.51% | 18% | renter cost burden; poverty; seasonal housing pressure; disability |
| 33 | Mattawamkeag | Penobscot | 56.41 | 698 | 28.21% | 7.4% | 30.22% | poverty; disability; long commutes; renter cost burden |
| 34 | Brownville | Piscataquis | 56.05 | 983 | 31.53% | 21.62% | 37.46% | long commutes; poverty; seasonal housing pressure; housing cost burden |
| 35 | Parsonsfield | York | 55.99 | 1,715 | 42.65% | 27.38% | 58.57% | renter cost burden; long commutes; housing cost burden; seasonal housing pressure |

## Top Housing Pressure Signals

| Rank | Town | County | Score | Population | Cost Burden | Seasonal Housing | Long Commute | Key Drivers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Allagash | Aroostook | 90.09 | 224 | 54.76% | 34.46% | 31.25% | housing cost burden; renter cost burden; poverty; seasonal housing pressure |
| 2 | Eustis | Franklin | 88.35 | 453 | 51.25% | 61.53% | 0% | housing cost burden; renter cost burden; seasonal housing pressure; poverty |
| 3 | Brighton | Somerset | 85.01 | 98 | 71.43% | 62.35% | 35.29% | housing cost burden; renter cost burden; poverty; seasonal housing pressure |
| 4 | North Washington UT | Washington | 83.69 | 620 | 46.26% | 60.06% | 4.57% | renter cost burden; poverty; seasonal housing pressure; disability |
| 5 | North Penobscot UT | Penobscot | 80.47 | 518 | 46.89% | 68.86% | 16.18% | renter cost burden; seasonal housing pressure; housing cost burden; poverty |
| 6 | Avon | Franklin | 75.78 | 359 | 42.75% | 44.31% | 27.63% | renter cost burden; seasonal housing pressure; housing cost burden; long commutes |
| 7 | West Paris | Oxford | 74.95 | 1,808 | 40% | 15.91% | 23.19% | renter cost burden; poverty; housing cost burden; long commutes |
| 8 | New Vineyard | Franklin | 74.69 | 607 | 33.64% | 39.41% | 20.61% | renter cost burden; seasonal housing pressure; poverty; children/family demand |
| 9 | Lee | Penobscot | 74.06 | 925 | 33.67% | 35% | 24.43% | renter cost burden; seasonal housing pressure; poverty; long commutes |
| 10 | Kingman UT | Penobscot | 73.21 | 138 | 24.36% | 37.1% | 26.67% | renter cost burden; poverty; seasonal housing pressure; long commutes |
| 11 | Boothbay Harbor | Lincoln | 73.17 | 2,096 | 39% | 44.45% | 4.79% | renter cost burden; seasonal housing pressure; older adults; housing cost burden |
| 12 | St. Albans | Somerset | 73 | 1,831 | 31.77% | 25.83% | 34.03% | renter cost burden; long commutes; poverty; disability |
| 13 | Orono | Penobscot | 72.05 | 11,902 | 46.29% | 1.43% | 3.56% | renter cost burden; poverty; housing cost burden; disability |
| 14 | Mount Chase | Penobscot | 71.88 | 280 | 37.39% | 53.71% | 16.67% | poverty; seasonal housing pressure; housing cost burden; disability |
| 15 | Cherryfield | Washington | 71.82 | 809 | 32.9% | 15.82% | 24.91% | renter cost burden; poverty; disability; long commutes |
| 16 | Chebeague Island | Cumberland | 71.53 | 555 | 42.39% | 47.47% | 17.05% | renter cost burden; seasonal housing pressure; older adults; housing cost burden |
| 17 | Blue Hill | Hancock | 71.45 | 2,813 | 58.75% | 28.44% | 7.9% | housing cost burden; renter cost burden; seasonal housing pressure; older adults |
| 18 | Machias | Washington | 71.18 | 2,020 | 43.85% | 0.71% | 9.98% | renter cost burden; poverty; housing cost burden; disability |
| 19 | Andover | Oxford | 71.11 | 679 | 36.92% | 44.86% | 9.03% | renter cost burden; seasonal housing pressure; housing cost burden; poverty |
| 20 | Madawaska | Aroostook | 70.86 | 3,853 | 43.77% | 13.91% | 0% | renter cost burden; housing cost burden; zero-car households; disability |
| 21 | Meddybemps | Washington | 70.76 | 139 | 51.79% | 44.08% | 13.51% | housing cost burden; renter cost burden; seasonal housing pressure; disability |
| 22 | Monson | Piscataquis | 70.6 | 596 | 42.15% | 47.47% | 16.67% | seasonal housing pressure; renter cost burden; housing cost burden; older adults |
| 23 | Athens | Somerset | 70.59 | 791 | 26.22% | 28.88% | 18.41% | renter cost burden; poverty; seasonal housing pressure; disability |
| 24 | Hamlin | Aroostook | 70.5 | 111 | 52.63% | 11.76% | 4% | housing cost burden; renter cost burden; disability; older adults |
| 25 | Lewiston | Androscoggin | 70.39 | 38,324 | 40.71% | 0.58% | 11.19% | renter cost burden; housing cost burden; poverty; zero-car households |
| 26 | Southwest Harbor | Hancock | 70.39 | 1,553 | 40.16% | 43.86% | 1.87% | renter cost burden; seasonal housing pressure; housing cost burden; older adults |
| 27 | Rumford | Oxford | 70.36 | 5,942 | 38.03% | 7.92% | 14.67% | renter cost burden; poverty; housing cost burden; disability |
| 28 | Orient | Aroostook | 70.09 | 137 | 24.07% | 74.91% | 0% | renter cost burden; poverty; seasonal housing pressure; older adults |
| 29 | Castine | Hancock | 69.84 | 1,362 | 34.69% | 43.75% | 3.4% | renter cost burden; seasonal housing pressure; housing cost burden; poverty |
| 30 | Grand Lake Stream | Washington | 69.64 | 169 | 34.26% | 47.06% | 0% | renter cost burden; older adults; seasonal housing pressure; housing cost burden |
| 31 | Crawford | Washington | 69.61 | 97 | 22% | 46.76% | 11.11% | renter cost burden; poverty; older adults; disability |
| 32 | Brooksville | Hancock | 69.4 | 853 | 42.86% | 45.67% | 4.26% | renter cost burden; seasonal housing pressure; housing cost burden; older adults |
| 33 | Trenton | Hancock | 69.39 | 1,599 | 31.94% | 29.92% | 15.97% | renter cost burden; seasonal housing pressure; poverty; housing cost burden |
| 34 | Parsonsfield | York | 69.28 | 1,715 | 42.65% | 27.38% | 58.57% | renter cost burden; long commutes; housing cost burden; seasonal housing pressure |
| 35 | Osborn | Hancock | 69.22 | 88 | 44.9% | 45.45% | 50% | renter cost burden; seasonal housing pressure; long commutes; housing cost burden |

## Strongest Infrastructure-Efficiency Proxies

| Rank | Town | County | Score | Population | Cost Burden | Seasonal Housing | Long Commute | Key Drivers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Portland | Cumberland | 84.36 | 68,854 | 41.49% | 5.16% | 6.59% | renter cost burden; housing cost burden; zero-car households; children/family demand |
| 2 | Scarborough | Cumberland | 65.24 | 23,215 | 35.42% | 7.69% | 4.55% | renter cost burden; housing cost burden; children/family demand; older adults |
| 3 | South Portland | Cumberland | 65.01 | 26,930 | 43.29% | 0.81% | 3.52% | renter cost burden; housing cost burden; children/family demand; older adults |
| 4 | Lewiston | Androscoggin | 62.55 | 38,324 | 40.71% | 0.58% | 11.19% | renter cost burden; housing cost burden; poverty; zero-car households |
| 5 | Falmouth | Cumberland | 62.02 | 12,755 | 24.96% | 3.67% | 6.53% | renter cost burden; children/family demand; housing cost burden; older adults |
| 6 | Bangor | Penobscot | 61.89 | 31,938 | 39.56% | 0.21% | 7.1% | renter cost burden; housing cost burden; poverty; disability |
| 7 | Westbrook | Cumberland | 61.29 | 20,775 | 37.02% | 0.52% | 3.74% | renter cost burden; housing cost burden; children/family demand; disability |
| 8 | Cape Elizabeth | Cumberland | 59.76 | 9,606 | 26.27% | 5.28% | 6.19% | children/family demand; renter cost burden; housing cost burden; older adults |
| 9 | Saco | York | 58.81 | 20,819 | 37.47% | 4.25% | 7.06% | renter cost burden; housing cost burden; children/family demand; disability |
| 10 | Cumberland | Cumberland | 57.86 | 8,647 | 32.31% | 1.8% | 9.33% | renter cost burden; children/family demand; housing cost burden; older adults |
| 11 | Gorham | Cumberland | 57.79 | 18,300 | 30.46% | 0% | 9.75% | renter cost burden; children/family demand; housing cost burden; older adults |
| 12 | Brunswick | Cumberland | 57.28 | 22,336 | 39.32% | 1.73% | 10.74% | renter cost burden; housing cost burden; children/family demand; older adults |
| 13 | Waterville | Kennebec | 56.03 | 17,077 | 38.81% | 0.26% | 5.78% | renter cost burden; poverty; housing cost burden; zero-car households |
| 14 | Kennebunk | York | 55.99 | 11,820 | 28.53% | 14.49% | 8.24% | renter cost burden; older adults; housing cost burden; children/family demand |
| 15 | Biddeford | York | 55.86 | 22,498 | 34.82% | 6.81% | 9.85% | renter cost burden; housing cost burden; poverty; children/family demand |
| 16 | Windham | Cumberland | 55.24 | 19,188 | 30.77% | 9% | 12.19% | renter cost burden; housing cost burden; children/family demand; long commutes |
| 17 | Auburn | Androscoggin | 54.63 | 24,602 | 42.58% | 0.99% | 13.3% | renter cost burden; housing cost burden; children/family demand; disability |
| 18 | Rockland | Knox | 54.49 | 7,035 | 41.31% | 3.55% | 1.84% | renter cost burden; housing cost burden; disability; older adults |
| 19 | Kittery | York | 54.46 | 10,473 | 36.06% | 4.41% | 7.77% | renter cost burden; housing cost burden; older adults; disability |
| 20 | Orono | Penobscot | 54.28 | 11,902 | 46.29% | 1.43% | 3.56% | renter cost burden; poverty; housing cost burden; disability |
| 21 | Augusta | Kennebec | 54.05 | 19,077 | 38.81% | 1.51% | 9.1% | renter cost burden; housing cost burden; poverty; disability |
| 22 | South Berwick | York | 54.04 | 7,670 | 41.39% | 0.54% | 6.08% | renter cost burden; housing cost burden; children/family demand; disability |
| 23 | Matinicus Isle | Knox | 53.78 | 48 | 33.33% | 71.79% | 0% | older adults; seasonal housing pressure; housing cost burden; children/family demand |
| 24 | Hampden | Penobscot | 53.59 | 7,896 | 23.79% | 3.16% | 8.18% | children/family demand; housing cost burden; renter cost burden; disability |
| 25 | Topsham | Sagadahoc | 52.79 | 9,706 | 31.23% | 0% | 8.49% | renter cost burden; housing cost burden; children/family demand; disability |
| 26 | Old Town | Penobscot | 52.72 | 7,470 | 41.56% | 1.44% | 4.71% | renter cost burden; poverty; housing cost burden; children/family demand |
| 27 | Yarmouth | Cumberland | 52.58 | 9,053 | 35.26% | 3.19% | 10.05% | renter cost burden; children/family demand; housing cost burden; poverty |
| 28 | North Yarmouth | Cumberland | 52.16 | 4,240 | 21.37% | 0.81% | 8.91% | renter cost burden; children/family demand; housing cost burden; older adults |
| 29 | York | York | 52 | 13,986 | 31.33% | 34.22% | 11.04% | renter cost burden; seasonal housing pressure; children/family demand; housing cost burden |
| 30 | Eliot | York | 51.86 | 7,146 | 45.7% | 3.44% | 8.04% | renter cost burden; housing cost burden; older adults; children/family demand |
| 31 | West Gardiner | Kennebec | 51.77 | 3,696 | 26.6% | 4.21% | 4.19% | renter cost burden; children/family demand; housing cost burden; disability |
| 32 | Freeport | Cumberland | 51.57 | 8,802 | 34.78% | 6.57% | 10.88% | renter cost burden; housing cost burden; children/family demand; older adults |
| 33 | Presque Isle | Aroostook | 51.29 | 8,736 | 37.44% | 0.43% | 3.19% | renter cost burden; housing cost burden; poverty; disability |
| 34 | Newcastle | Lincoln | 51.22 | 1,913 | 25.86% | 14.1% | 1.98% | children/family demand; housing cost burden; disability; older adults |
| 35 | Cyr | Aroostook | 50.97 | 59 | 17.39% | 0% | 0% | older adults; disability; housing cost burden; children/family demand |

## Focus Towns

| Town | County | MVP Score | Housing Need | Resilience Priority | Infrastructure Proxy | Lane |
| --- | --- | --- | --- | --- | --- | --- |
| Brunswick | Cumberland | 52.85 | 54.89 | 31.91 | 57.28 | monitor and screen after hazard-layer ingestion |
| Cumberland | Cumberland | 44.1 | 43.07 | 23.93 | 57.86 | monitor and screen after hazard-layer ingestion |
| Falmouth | Cumberland | 44.17 | 38.01 | 22.21 | 62.02 | monitor and screen after hazard-layer ingestion |
| Gorham | Cumberland | 45.45 | 39.38 | 23.73 | 57.79 | monitor and screen after hazard-layer ingestion |
| Hollis | York | 40.88 | 45.91 | 29.18 | 45.39 | monitor and screen after hazard-layer ingestion |
| Kennebunk | York | 44.66 | 47.09 | 32.02 | 55.99 | monitor and screen after hazard-layer ingestion |
| Portland | Cumberland | 73.04 | 67.34 | 35.78 | 84.36 | infrastructure-efficient affordable housing search |
| Scarborough | Cumberland | 50.86 | 50.58 | 26.64 | 65.24 | infrastructure-efficient affordable housing search |
| South Portland | Cumberland | 56.66 | 56.97 | 28.21 | 65.01 | infrastructure-efficient affordable housing search |
| Westbrook | Cumberland | 52.09 | 51.15 | 25.84 | 61.29 | infrastructure-efficient affordable housing search |

## Next Spatial Layers To Ingest

| Priority | Layer | Why It Matters |
| --- | --- | --- |
| 1 | FEMA NFHL flood zones | Turns town screening into real flood-exposure screening. |
| 2 | Maine Geological Survey SLR/storm-surge scenarios | Identifies coastal land that may be unsuitable under future sea-level and storm scenarios. |
| 3 | USFWS NWI wetlands and Maine conservation lands | Creates hard environmental exclusions. |
| 4 | USGS 3DEP DEM slope/elevation | Adds low-lying land, slope, and terrain buildability constraints. |
| 5 | MaineDOT roads, bridges, and culverts | Adds infrastructure access and vulnerability. |
| 6 | Parcels and zoning for pilot towns | Converts statewide screening into local site-selection products. |

## Source Context

- U.S. Census Bureau ACS 2024 5-year table-based Summary File, loaded in `acs_town_demographics`.
- The project schema now includes empty PostGIS tables for hazard zones, environmental constraints, infrastructure assets, and candidate units.
- Hazard overlay status for this MVP: pending FEMA NFHL, MGS SLR/storm-surge, NWI wetlands, conservation, DEM, roads/bridges/culverts overlay.
