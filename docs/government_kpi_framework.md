# Maine Government KPI Framework

This project now includes a statewide public-sector KPI layer that turns ACS county-subdivision indicators into repeatable town-level screening scores. The goal is to help answer practical Maine planning questions before the project adds richer parcel, transit, broadband, climate, health, and facility datasets.

## Core Questions

- Which towns should be prioritized for transportation equity and last-mile mobility planning?
- Which towns show housing affordability, cost-burden, seasonal-pressure, or production-planning signals?
- Where will aging-in-place, disability access, and healthcare coordination matter most?
- Which towns should be watched for broadband and digital-equity intervention?
- Where do food/basic-needs pressure and family-service demand overlap?
- Which towns need workforce-support infrastructure such as housing, commute relief, childcare/family services, and broadband?
- Where can compact growth and lower-emission mobility reduce transportation burden?

## KPI Scores

| KPI | Main Inputs | What It Helps Answer |
| --- | --- | --- |
| Government priority score | Weighted blend of housing, mobility, aging, digital, health, food/basic-needs, workforce, and climate-mobility scores | Which towns deserve first-pass policy attention across several domains? |
| Housing pressure score | Housing cost burden, renter burden, poverty, seasonal housing share, zero-car households, population scale | Where may housing production, affordability, or seasonal-market pressure matter most? |
| Transportation equity score | Zero-car households, long commutes, poverty, disability, age 65+ | Where are mobility investments most urgent for vulnerable households? |
| Aging-in-place score | Age 65+, disability, zero-car households, no internet/subscription, housing cost burden | Where should senior mobility, accessible housing, home care, and healthcare coordination be prioritized? |
| Digital equity score | No internet/subscription, poverty, age 65+, disability, rural service gap | Where may broadband affordability, adoption, or digital skills support matter most? |
| Health access pressure score | Disability, age 65+, poverty, zero-car households, rural service gap | Where do health access and transportation vulnerability overlap? |
| Food/basic-needs score | Poverty, zero-car households, children under 18, disability, age 65+, digital gap | Where might food access and household-stability interventions be most needed? |
| Workforce-support score | Population scale, long commutes, housing cost burden, children under 18, poverty, digital gap | Where can housing, childcare/family services, commute relief, and broadband strengthen workforce participation? |
| Climate mobility opportunity score | Population scale, drive-alone commute share, long commute share, zero-car households, non-drive/WFH patterns, housing burden | Where can compact growth and transportation choices reduce emissions and household burden? |
| Child/family service score | Children under 18, poverty, housing cost burden, zero-car households, digital gap | Where should family services, school-adjacent supports, and childcare-adjacent planning be watched? |

## Current Limits

These KPIs are statewide screening metrics, not final eligibility decisions. The current statewide model uses ACS demographic, housing, commute, and internet-access indicators. It does not yet include parcel prices, zoning, flood risk, broadband fabric/BSL availability, GTFS service coverage, road safety, facility travel time, food retail access, childcare locations, school quality, municipal tax rates, or capital improvement plans.

## Generated Outputs

- `reports/maine_government_priority_kpi_report.md`
- `reports/maine_government_priority_kpi_report.html`
- `reports/maine_government_priority_kpi_report.pdf`
- `reports/maine_government_priority_kpi_rankings.csv`

## Policy Source Context

- MaineHousing, State of Maine Housing Production Needs Study.
- MaineDOT, Maine 2024-2028 Locally Coordinated Plan.
- Maine DHHS, 2024-2029 State Health Improvement Plan.
- Maine DHHS/OADS, State Plan on Aging 2025-2028 and Age-Friendly State Plan.
- Maine Connectivity Authority, Digital Equity Plan.
- Maine DECD, 2024 Economic Development Strategy Reset.
- Maine Climate Plan, Maine Won't Wait.
