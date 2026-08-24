from __future__ import annotations

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis.ipynb"


def md(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


cells = [
    md(
        """
# Multi-Branch Retail Demand Intelligence & Continuous Improvement

**Independent Kaggle Competition Project — CRISP-DM**  
**Author:** Freska Prisia Putri

This notebook translates multi-source grocery retail data into recurring performance reporting,
store and product-family diagnostics, a leakage-safe 16-day demand forecast, and an actionable
continuous-improvement backlog.

**Data source:** [Store Sales — Time Series Forecasting](https://www.kaggle.com/competitions/store-sales-time-series-forecasting/overview)

> The competition files remain governed by Kaggle's competition rules. Raw CSV files are not
> redistributed by this repository; generated aggregates and analytical evidence are versioned.
"""
    ),
    md(
        """
## 1. Business understanding

The operating decision is not simply *how much will sell?* The analysis must also explain where
demand is changing, which store–family combinations need review, how reliable the forecast is,
and how analytical findings should become repeatable system and process improvements.

Business questions:

1. How is demand trending by month, store, and product family?
2. Which stores and families are growing or declining on an aligned-period basis?
3. Where is the forecast materially over- or under-estimating demand?
4. What actions, owners, monitoring cadence, and acceptance criteria should follow?
"""
    ),
    code(
        """
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path.cwd()
if not (ROOT / "data").exists():
    ROOT = ROOT.parent

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams.update({"figure.figsize": (11, 5), "axes.titlesize": 13, "axes.labelsize": 10})

with open(ROOT / "validation" / "source_profile.json", encoding="utf-8") as f:
    profile = json.load(f)
with open(ROOT / "validation" / "model_summary.json", encoding="utf-8") as f:
    model_summary = json.load(f)

monthly = pd.read_csv(ROOT / "data" / "reporting" / "monthly_report.csv", parse_dates=["month_start"])
branches = pd.read_csv(ROOT / "data" / "reporting" / "branch_scorecard.csv")
families = pd.read_csv(ROOT / "data" / "reporting" / "family_scorecard.csv")
forecast = pd.read_csv(ROOT / "data" / "processed" / "forecast_validation.csv", parse_dates=["date"])
forecast_store = pd.read_csv(ROOT / "data" / "reporting" / "forecast_by_store.csv")
actions = pd.read_csv(ROOT / "data" / "reporting" / "action_register.csv")

print(f"Project root: {ROOT}")
print(f"Validation rows loaded: {len(forecast):,}")
"""
    ),
    md("## 2. Data understanding"),
    code(
        """
quality_summary = pd.DataFrame({
    "Check": [
        "Training rows", "Training date range", "Stores", "Product families",
        "Duplicate training IDs", "Negative sales", "Oil price nulls",
        "Holiday dates with multiple records", "Test grid rows"
    ],
    "Result": [
        f"{profile['files']['train.csv']['rows']:,}",
        f"{profile['files']['train.csv']['date_min']} to {profile['files']['train.csv']['date_max']}",
        profile['files']['stores.csv']['rows'], profile['files']['train.csv']['distinct_families'],
        profile['files']['train.csv']['duplicate_ids'], profile['files']['train.csv']['negative_sales'],
        profile['files']['oil.csv']['nulls']['dcoilwtico'], profile['integrity']['holiday_dates_with_multiple_records'],
        profile['files']['test.csv']['rows'],
    ],
    "Decision": [
        "Use chunked profiling and aggregate analytical tables",
        "Use time-based validation; never random split",
        "Store dimension", "Family dimension", "Pass", "Pass",
        "Impute or carry forward only in models that use oil",
        "Aggregate holiday attributes before joining to prevent row multiplication",
        "Complete 16-day store-family forecast horizon",
    ],
})
quality_summary
"""
    ),
    md(
        """
### Trust boundaries

- Sales are non-negative, but zero sales are legitimate and frequent; they are not treated as
  missing values.
- Promotion counts are observed attributes, not causal treatment estimates.
- Four December 25 dates are absent from the training calendar; no synthetic sales rows are added.
- August 2017 is partial through 15 August, so year-over-year reporting uses aligned dates.
"""
    ),
    md("## 3. Data preparation"),
    code(
        """
monthly["year"] = monthly["month_start"].dt.year
monthly["month_label"] = monthly["month_start"].dt.strftime("%Y-%m")
monthly_complete = monthly.loc[monthly["is_complete_month"]].copy()

print("Prepared analytical grains")
display(pd.DataFrame({
    "Dataset": ["monthly_store_family", "daily_store_performance", "forecast_validation"],
    "Grain": ["month × store × family", "date × store", "date × store × family"],
    "Primary use": ["BI slicing and trend analysis", "traffic and store monitoring", "forecast QA"],
}))
"""
    ),
    code(
        """
fig, ax = plt.subplots()
ax.plot(monthly["month_start"], monthly["unit_sales"], color="#0B5E75", linewidth=2)
ax.scatter(monthly.loc[~monthly["is_complete_month"], "month_start"],
           monthly.loc[~monthly["is_complete_month"], "unit_sales"],
           color="#D97706", label="Partial month", zorder=3)
ax.set(title="Monthly unit sales trend", xlabel="Month", ylabel="Units sold")
ax.legend(frameon=False)
plt.tight_layout()
plt.show()
"""
    ),
    code(
        """
top_branches = branches.nlargest(12, "current_ytd_sales").sort_values("current_ytd_sales")
fig, ax = plt.subplots()
labels = [f"Store {s} — {c}" for s, c in zip(top_branches.store_nbr, top_branches.city)]
ax.barh(labels, top_branches["current_ytd_sales"], color="#168F8B")
ax.set(title="Top stores by aligned 2017 YTD sales", xlabel="Unit sales", ylabel="")
plt.tight_layout()
plt.show()
"""
    ),
    md(
        """
## 4. Modeling

The deployed baseline is a recursive seasonal median that uses only information available before
each forecasted date. It uses recent weekly lags at the store–family level and recursively feeds
predictions into later horizon days. The validation window mirrors the test horizon: 16 consecutive
days.

This deliberately transparent baseline establishes a reproducible benchmark before more complex
promotion-aware models such as LightGBM are considered.
"""
    ),
    code(
        """
actual = forecast["actual_sales"].clip(lower=0)
pred = forecast["forecast_sales"].clip(lower=0)
rmsle = np.sqrt(np.mean((np.log1p(pred) - np.log1p(actual)) ** 2))
bias = (pred.sum() - actual.sum()) / actual.sum()
wape = (pred - actual).abs().sum() / actual.sum()

metric_check = pd.Series({
    "Validation RMSLE": rmsle,
    "Forecast bias": bias,
    "WAPE": wape,
    "Forecast accuracy (1-WAPE)": max(0, 1 - wape),
    "Validation rows": len(forecast),
})
metric_check.to_frame("Value")
"""
    ),
    md("## 5. Evaluation"),
    code(
        """
daily_forecast = forecast.groupby("date", as_index=False).agg(
    actual_sales=("actual_sales", "sum"), forecast_sales=("forecast_sales", "sum")
)

fig, ax = plt.subplots()
ax.plot(daily_forecast["date"], daily_forecast["actual_sales"], label="Actual", color="#173B57", linewidth=2)
ax.plot(daily_forecast["date"], daily_forecast["forecast_sales"], label="Forecast", color="#D97706", linewidth=2)
ax.set(title="Leakage-safe 16-day holdout: actual vs forecast", xlabel="Date", ylabel="Unit sales")
ax.legend(frameon=False)
plt.xticks(rotation=30)
plt.tight_layout()
plt.show()
"""
    ),
    code(
        """
risk = forecast_store.sort_values("wape", ascending=False).head(12).copy()
risk["label"] = [f"Store {s} — {c}" for s, c in zip(risk.store_nbr, risk.city)]

fig, ax = plt.subplots()
sns.barplot(data=risk, y="label", x="wape", color="#C45A3A", ax=ax)
ax.set(title="Stores with the highest forecast WAPE", xlabel="WAPE", ylabel="")
ax.xaxis.set_major_formatter(lambda x, pos: f"{x:.0%}")
plt.tight_layout()
plt.show()
"""
    ),
    code(
        """
evaluation = forecast_store[["store_nbr", "city", "actual_sales", "forecast_sales", "forecast_bias", "wape", "forecast_accuracy"]].copy()
evaluation["forecast_bias"] = evaluation["forecast_bias"].map(lambda x: f"{x:.1%}")
evaluation["wape"] = evaluation["wape"].map(lambda x: f"{x:.1%}")
evaluation["forecast_accuracy"] = evaluation["forecast_accuracy"].map(lambda x: f"{x:.1%}")
evaluation.sort_values("wape", ascending=False).head(10)
"""
    ),
    md("## 6. Deployment and continuous improvement"),
    code(
        """
display(actions.head(10))
"""
    ),
    md(
        """
### Decision and system requirements

1. Surface store–family exceptions when WAPE is high or absolute bias breaches the agreed threshold.
2. Store each forecast run with model version, run date, horizon, prediction, actual, and error.
3. Let business users filter KPI results by date, store, city, state, type, cluster, and family.
4. Refresh monthly, quarterly, and annual reporting from the same governed metric definitions.
5. Require an owner, status, target date, and post-implementation review for every improvement action.

### Management conclusion

- The baseline processes **28,512** validation rows without missing or negative predictions.
- Validation RMSLE is **0.551**, with **−1.5% aggregate bias** and **17.2% WAPE**.
- The model is suitable as a transparent benchmark, not as a final production forecast.
- The next modeling iteration should compare promotion-aware LightGBM against this baseline using
  the same fixed time window and should only be adopted when it improves RMSLE without creating
  unacceptable store- or family-level bias.
"""
    ),
]

notebook = nbf.v4.new_notebook(cells=cells)
notebook["metadata"]["kernelspec"] = {
    "display_name": "Python 3",
    "language": "python",
    "name": "python3",
}
notebook["metadata"]["language_info"] = {"name": "python", "version": "3.12"}
nbf.write(notebook, OUTPUT)
print(f"Wrote {OUTPUT}")
