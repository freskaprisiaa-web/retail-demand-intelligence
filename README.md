# Multi-Branch Retail Demand Intelligence & Continuous Improvement

**Independent Kaggle Competition Project — CRISP-DM**  
**Freska Prisia Putri**

An end-to-end analytics project that turns multi-source grocery retail data into demand forecasts, recurring management reporting, branch and product diagnostics, business requirements, and a measurable continuous-improvement workflow.

## Business purpose

Retail teams need to anticipate demand across stores and product families while accounting for promotions, holidays, transactions, store characteristics, and external conditions. The project answers four operating questions:

1. Where is demand growing, declining, or unusually volatile?
2. Which stores and product families need closer replenishment attention?
3. How strongly do promotions, holidays, and transaction traffic relate to demand?
4. How accurate is the next-16-day forecast, where is it biased, and what action should follow?

## Data source and competition

- [Kaggle competition overview](https://www.kaggle.com/competitions/store-sales-time-series-forecasting/overview)
- [Competition data](https://www.kaggle.com/competitions/store-sales-time-series-forecasting/data)
- Evaluation metric: Root Mean Squared Logarithmic Error (RMSLE)

The competition is ongoing with a rolling leaderboard. Source data is not redistributed in this repository; download the seven competition CSV files and place them in `data/`.

## CRISP-DM workflow

| Phase | Evidence in this repository |
|---|---|
| Business Understanding | Business questions, stakeholders, KPI dictionary, AS-IS process, and requirement scope |
| Data Understanding | Source profiling, data dictionary, grain checks, null/duplicate/integrity tests |
| Data Preparation | Reproducible Python pipeline, time features, aggregates, BI exports, and SQLite warehouse |
| Modeling | Leakage-safe recursive seasonal baseline and a governed next-experiment plan for promotion-aware boosting |
| Evaluation | RMSLE, bias, error by store/family, and forecast monitoring tables |
| Deployment | Excel management pack, Power BI-ready model, SQL analysis, HTML dashboard, and improvement backlog |

## Dataset at a glance

- 3,000,888 daily store-family training rows
- 54 stores and 33 product families
- Training period: 2013-01-01 to 2017-08-15
- Forecast horizon: 2017-08-16 to 2017-08-31 (16 days; 28,512 predictions)
- Additional sources: transactions, stores, oil price, holidays/events, and promotion counts

## Deliverables

| Deliverable | Location | Purpose |
|---|---|---|
| Analysis notebook | `analysis.ipynb` | Reader-facing CRISP-DM analysis and model evaluation |
| Python pipeline | `src/` | Reproducible profiling, aggregation, forecasting, and output generation |
| SQL warehouse | `retail_demand.sqlite` | Star-schema tables and reusable analysis queries |
| Power BI package | `powerbi/` + `data/powerbi/` | Prepared tables, DAX measures, and page-by-page build guide |
| Excel reporting pack | `Retail_Demand_Intelligence.xlsx` | Monthly, quarterly, annual, branch, forecast, and action reporting |
| Portable dashboard | `dashboard.html` | Browser-based executive summary |
| Business documentation | `docs/` | KPI definitions, BPM, system requirements, and reporting cadence |
| Kaggle submission | `submission.csv` | Predictions in the required `id,sales` format |

## Validated results

- Aligned 2017 YTD sales: **194.2 million units**, up **10.0%** from the same 2016 window.
- Fixed 16-day holdout: **0.551 RMSLE**, **−1.5% forecast bias**, and **17.2% WAPE**.
- Test submission: **28,512** unique predictions with no null or negative values.
- Daily store integration: **90,936** unique date-store rows combining sales, promotions, transactions, oil prices, and locale-aware holidays.
- Descriptive driver evidence: transactions had the strongest positive association with daily store sales (**r = 0.837**); promotion exposure was moderately positive (**r = 0.359**). Holiday store-days averaged **19.1%** higher sales than non-holiday store-days. These are associations, not causal estimates.

The complete automated QA evidence is available in `validation/VALIDATION_SUMMARY.md`.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src/profile_data.py --data-dir data --output validation/source_profile.json
python src/build_analytics.py --data-dir data
python src/build_notebook.py
jupyter nbconvert --to notebook --execute analysis.ipynb --inplace
python src/build_dashboard.py
python src/validate_notebook.py
python src/validate_project.py
```

Raw competition CSV files are intentionally ignored by Git. Generated aggregate and BI tables are small enough to review and version.

## Portfolio competencies demonstrated

- Python and SQL analysis on more than three million records
- Data quality, multi-source integration, dimensional modeling, and traceable KPI definitions
- Time-series validation and demand forecasting without future-data leakage
- Excel management reporting and Power BI semantic-model design
- Business analysis: AS-IS/TO-BE process, functional requirements, acceptance criteria, and improvement backlog
- Monthly, quarterly, and annual reporting with decision-focused recommendations
