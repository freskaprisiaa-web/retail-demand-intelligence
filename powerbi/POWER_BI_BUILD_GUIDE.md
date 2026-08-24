# Power BI build guide

## 1. Import

Use **Get data → Text/CSV** and import all files from `data/powerbi/`:

- `dim_date.csv`
- `dim_store.csv`
- `dim_family.csv`
- `fact_monthly_store_family.csv`
- `fact_daily_store.csv`
- `fact_forecast_validation.csv`

Set date columns to **Date**, keys/counts to **Whole number**, and sales/error fields to
**Decimal number**. Use the provided theme from `powerbi/theme_modern_navy_teal.json`.

## 2. Relationships

Create single-direction, one-to-many relationships from dimensions to facts:

| One side | Many side |
|---|---|
| `dim_date[full_date]` | `fact_monthly_store_family[month_start]` |
| `dim_date[full_date]` | `fact_daily_store[date]` |
| `dim_date[full_date]` | `fact_forecast_validation[date]` |
| `dim_store[store_nbr]` | each fact table's `store_nbr` |
| `dim_family[family]` | monthly and forecast facts' `family` |

Mark `dim_date` as the date table using `full_date`. Hide technical keys from report view.

## 3. Measures

Create a blank table named `KPI_Measures` and add every measure from
`powerbi/dax_measures.dax`. Format percentages to one decimal, RMSLE to three decimals, and sales
to a whole number with a thousands separator.

## 4. Page 1 — Executive Overview

- Slicers: Year, State, City, Store, Family.
- Cards: Unit Sales, Revenue YoY Proxy %, Promotion Share %, Units per Transaction.
- Line chart: `dim_date[month_start]` versus Unit Sales and Units Previous Year.
- Horizontal bar: Unit Sales by store/city.
- Matrix: store, Unit Sales, Revenue YoY Proxy %, Forecast WAPE %, Reporting Scope.
- Add a visible note that August 2017 is partial through 15 August.

## 5. Page 2 — Forecast Monitoring

- Cards: Forecast RMSLE, Forecast WAPE %, Forecast Bias %, Forecast Accuracy %.
- Line chart: date versus Forecast Actual Sales and Forecast Sales.
- Bar chart: Forecast WAPE % by store.
- Heatmap/matrix: store × family with Forecast WAPE % conditional formatting.
- Detail table: date, store, family, actual, forecast, absolute error, percentage error.

## 6. Page 3 — Demand Drivers

- Line chart: Unit Sales and Promotion Units by month.
- Scatter: Transactions versus daily Unit Sales; color by store type.
- Bar chart: Unit Sales by family.
- Decomposition tree: Unit Sales → state → city → store type → store → family.

## 7. QA before saving

1. Unit Sales total equals the reporting/Excel control total for the same filter window.
2. Forecast RMSLE rounds to `0.551` on the full validation set.
3. Forecast Bias rounds to `-1.5%`; WAPE rounds to `17.2%`.
4. August 2017 is visibly labeled partial.
5. No many-to-many or bidirectional relationship is active.
6. Every visual has a clear title, business unit, and meaningful tooltip.

