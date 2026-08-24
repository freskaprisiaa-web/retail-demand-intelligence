# Business Requirements Document

## Problem statement

Historical sales, promotions, store attributes, transaction traffic, holidays, and external indicators sit in separate files. Analysts need a repeatable way to combine them, monitor demand, forecast the next 16 days, and turn forecast exceptions into clear replenishment and promotion-review actions.

## Stakeholders

| Stakeholder | Decision supported |
|---|---|
| Retail management | Review growth, demand mix, and branch exceptions |
| Store operations | Prioritize high-risk store-family combinations |
| Commercial/promotion team | Evaluate promotion dependency and lift |
| Inventory planning | Use forecast and bias to adjust replenishment |
| Data/IT team | Maintain trusted data model, refresh, and controls |

## Functional requirements

| ID | Requirement | Acceptance criterion |
|---|---|---|
| FR-01 | Ingest all seven competition CSV sources | Row counts and required columns reconcile to the source profile |
| FR-02 | Validate keys, nulls, dates, and domain rules | Automated report identifies failures and severity |
| FR-03 | Provide monthly, quarterly, and annual KPIs | Period filters reconcile to the same metric definitions |
| FR-04 | Diagnose demand by store and family | Users can rank growth, volatility, promotion, and forecast error |
| FR-05 | Forecast the 16-day horizon | Output contains exactly one non-negative prediction per test ID |
| FR-06 | Monitor model quality | RMSLE, bias, and segmented errors are visible |
| FR-07 | Support action tracking | Each exception can be assigned an owner, action, due date, and status |
| FR-08 | Export to Excel and Power BI | Prepared tables load without manual type correction |

## Non-functional requirements

- Reproducible: deterministic code and explicit parameters.
- Auditable: KPI and model definitions are documented.
- Performant: large raw data is aggregated before Excel/Power BI consumption.
- Maintainable: source paths, model horizon, and refresh window are configurable.
- Safe: source data is not redistributed and no credentials are committed.

