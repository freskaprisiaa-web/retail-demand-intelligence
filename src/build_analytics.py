"""Build analytical aggregates, validation forecasts, submission, and SQLite tables."""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


FORECAST_HORIZON = 16


def rmsle(actual: np.ndarray, forecast: np.ndarray) -> float:
    actual = np.clip(actual.astype(float), 0, None)
    forecast = np.clip(forecast.astype(float), 0, None)
    return float(np.sqrt(np.mean((np.log1p(forecast) - np.log1p(actual)) ** 2)))


def recursive_weekly_forecast(
    history: pd.DataFrame,
    future: pd.DataFrame,
) -> pd.DataFrame:
    """Forecast each store-family using only values available before each prediction."""
    history_values = {
        (int(row.store_nbr), str(row.family), pd.Timestamp(row.date)): float(row.sales)
        for row in history.itertuples(index=False)
    }
    fallback = history.groupby(["store_nbr", "family"], observed=True)["sales"].median()
    predictions: list[dict] = []

    for target_date in sorted(pd.to_datetime(future["date"].unique())):
        day_rows = future[pd.to_datetime(future["date"]) == target_date]
        for row in day_rows.itertuples(index=False):
            store = int(row.store_nbr)
            family = str(row.family)
            lag_values = [
                history_values.get((store, family, target_date - pd.Timedelta(days=lag)))
                for lag in (7, 14, 21, 28)
            ]
            available = [value for value in lag_values if value is not None]
            prediction = float(np.median(available)) if available else float(fallback.get((store, family), 0.0))
            prediction = max(prediction, 0.0)
            history_values[(store, family, target_date)] = prediction
            predictions.append(
                {
                    "id": int(row.id) if hasattr(row, "id") else None,
                    "date": target_date,
                    "store_nbr": store,
                    "family": family,
                    "forecast_sales": prediction,
                }
            )
    return pd.DataFrame(predictions)


def build_date_dimension(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    dates = pd.DataFrame({"full_date": pd.date_range(start, end, freq="D")})
    dates["date_key"] = dates["full_date"].dt.strftime("%Y%m%d").astype(int)
    dates["year"] = dates["full_date"].dt.year
    dates["quarter"] = "Q" + dates["full_date"].dt.quarter.astype(str)
    dates["month_number"] = dates["full_date"].dt.month
    dates["month_name"] = dates["full_date"].dt.month_name()
    dates["week_of_year"] = dates["full_date"].dt.isocalendar().week.astype(int)
    dates["day_name"] = dates["full_date"].dt.day_name()
    dates["is_weekend"] = dates["full_date"].dt.dayofweek.ge(5).astype(int)
    dates["is_payday"] = (
        dates["full_date"].dt.day.eq(15)
        | dates["full_date"].eq(dates["full_date"] + pd.offsets.MonthEnd(0))
    ).astype(int)
    dates["month_start"] = dates["full_date"].dt.to_period("M").dt.to_timestamp()
    dates["full_date"] = dates["full_date"].dt.strftime("%Y-%m-%d")
    dates["month_start"] = dates["month_start"].dt.strftime("%Y-%m-%d")
    return dates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    root = args.output_root.resolve()
    processed_dir = root / "data" / "processed"
    powerbi_dir = root / "data" / "powerbi"
    reporting_dir = root / "data" / "reporting"
    validation_dir = root / "validation"
    processed_dir.mkdir(parents=True, exist_ok=True)
    powerbi_dir.mkdir(parents=True, exist_ok=True)
    reporting_dir.mkdir(parents=True, exist_ok=True)
    validation_dir.mkdir(parents=True, exist_ok=True)

    train = pd.read_csv(
        data_dir / "train.csv",
        dtype={"id": "int64", "store_nbr": "int16", "family": "category", "sales": "float32", "onpromotion": "int32"},
        parse_dates=["date"],
    )
    test = pd.read_csv(
        data_dir / "test.csv",
        dtype={"id": "int64", "store_nbr": "int16", "family": "category", "onpromotion": "int32"},
        parse_dates=["date"],
    )
    stores = pd.read_csv(data_dir / "stores.csv")
    transactions = pd.read_csv(data_dir / "transactions.csv", parse_dates=["date"])
    oil = pd.read_csv(data_dir / "oil.csv", parse_dates=["date"])
    holidays = pd.read_csv(data_dir / "holidays_events.csv", parse_dates=["date"])

    train["month_start"] = train["date"].dt.to_period("M").dt.to_timestamp()
    monthly = (
        train.groupby(["month_start", "store_nbr", "family"], observed=True)
        .agg(
            unit_sales=("sales", "sum"),
            promotion_units=("onpromotion", "sum"),
            observed_days=("date", "nunique"),
            zero_sales_days=("sales", lambda values: int((values == 0).sum())),
        )
        .reset_index()
    )
    monthly["month_start"] = monthly["month_start"].dt.strftime("%Y-%m-%d")

    daily_store = (
        train.groupby(["date", "store_nbr"], observed=True)
        .agg(unit_sales=("sales", "sum"), promotion_units=("onpromotion", "sum"))
        .reset_index()
        .merge(transactions, on=["date", "store_nbr"], how="left", validate="one_to_one")
    )

    # Oil is a national daily signal. Preserve whether the original value was missing,
    # then fill only within the date series so every store-date retains a usable value.
    oil = oil.sort_values("date").copy()
    oil["oil_price_was_missing"] = oil["dcoilwtico"].isna().astype(int)
    oil["oil_price_wti"] = oil["dcoilwtico"].ffill().bfill()
    daily_store = daily_store.merge(
        oil[["date", "oil_price_wti", "oil_price_was_missing"]],
        on="date",
        how="left",
        validate="many_to_one",
    )

    # Resolve the holiday locale before joining: national events apply to every store,
    # regional events to matching states, and local events to matching cities.
    active_holidays = holidays.loc[~holidays["transferred"]].copy()
    store_scope = stores[["store_nbr", "city", "state"]]
    holiday_frames = []
    national = active_holidays.loc[active_holidays["locale"].eq("National")].merge(
        store_scope[["store_nbr"]], how="cross"
    )
    holiday_frames.append(national)
    regional = active_holidays.loc[active_holidays["locale"].eq("Regional")].merge(
        store_scope, left_on="locale_name", right_on="state", how="inner"
    )
    holiday_frames.append(regional)
    local = active_holidays.loc[active_holidays["locale"].eq("Local")].merge(
        store_scope, left_on="locale_name", right_on="city", how="inner"
    )
    holiday_frames.append(local)
    store_holidays = pd.concat(holiday_frames, ignore_index=True)
    store_holidays = (
        store_holidays.groupby(["date", "store_nbr"], as_index=False)
        .agg(
            holiday_event_count=("description", "nunique"),
            holiday_descriptions=("description", lambda values: " | ".join(sorted(set(values)))),
        )
    )
    daily_store = daily_store.merge(
        store_holidays,
        on=["date", "store_nbr"],
        how="left",
        validate="one_to_one",
    )
    daily_store["holiday_event_count"] = daily_store["holiday_event_count"].fillna(0).astype(int)
    daily_store["is_holiday"] = daily_store["holiday_event_count"].gt(0).astype(int)
    daily_store["holiday_descriptions"] = daily_store["holiday_descriptions"].fillna("")
    daily_store["units_per_transaction"] = daily_store["unit_sales"] / daily_store["transactions"].replace(0, np.nan)

    driver_relationships = pd.DataFrame(
        [
            {
                "relationship": "Promotion units vs unit sales",
                "measure": "Pearson correlation",
                "value": daily_store["promotion_units"].corr(daily_store["unit_sales"]),
                "interpretation": "Descriptive association; not a causal promotion effect",
            },
            {
                "relationship": "Transactions vs unit sales",
                "measure": "Pearson correlation",
                "value": daily_store["transactions"].corr(daily_store["unit_sales"]),
                "interpretation": "Descriptive traffic relationship",
            },
            {
                "relationship": "WTI oil price vs unit sales",
                "measure": "Pearson correlation",
                "value": daily_store["oil_price_wti"].corr(daily_store["unit_sales"]),
                "interpretation": "National time-series association; confounding is expected",
            },
            {
                "relationship": "Holiday vs non-holiday unit sales",
                "measure": "Mean difference ratio",
                "value": (
                    daily_store.loc[daily_store["is_holiday"].eq(1), "unit_sales"].mean()
                    / daily_store.loc[daily_store["is_holiday"].eq(0), "unit_sales"].mean()
                    - 1
                ),
                "interpretation": "Unadjusted descriptive lift; not a causal estimate",
            },
        ]
    )

    validation_start = train["date"].max() - pd.Timedelta(days=FORECAST_HORIZON - 1)
    history = train[train["date"] < validation_start][["date", "store_nbr", "family", "sales"]].copy()
    validation_actual = train[train["date"] >= validation_start][["id", "date", "store_nbr", "family", "sales"]].copy()
    validation_features = validation_actual.drop(columns="sales")
    validation_forecast = recursive_weekly_forecast(history, validation_features)
    validation = validation_actual.merge(
        validation_forecast.drop(columns="id"),
        on=["date", "store_nbr", "family"],
        how="left",
        validate="one_to_one",
    ).rename(columns={"sales": "actual_sales"})
    validation["absolute_error"] = (validation["forecast_sales"] - validation["actual_sales"]).abs()
    validation["absolute_percentage_error"] = validation["absolute_error"] / validation["actual_sales"].clip(lower=1)
    validation_score = rmsle(validation["actual_sales"].to_numpy(), validation["forecast_sales"].to_numpy())
    validation_bias = float(
        (validation["forecast_sales"].sum() - validation["actual_sales"].sum())
        / validation["actual_sales"].sum()
    )
    validation_wape = float(validation["absolute_error"].sum() / validation["actual_sales"].sum())

    monthly_report = monthly.groupby("month_start", as_index=False).agg(
        unit_sales=("unit_sales", "sum"),
        promotion_units=("promotion_units", "sum"),
    )
    monthly_report["month_start"] = pd.to_datetime(monthly_report["month_start"])
    monthly_report["prior_month_sales"] = monthly_report["unit_sales"].shift(1)
    monthly_report["growth_mom"] = monthly_report["unit_sales"] / monthly_report["prior_month_sales"] - 1
    monthly_report["prior_year_sales"] = monthly_report["unit_sales"].shift(12)
    monthly_report["growth_yoy"] = monthly_report["unit_sales"] / monthly_report["prior_year_sales"] - 1
    monthly_report["is_complete_month"] = monthly_report["month_start"].dt.to_period("M") < train["date"].max().to_period("M")
    monthly_report["month_start"] = monthly_report["month_start"].dt.strftime("%Y-%m-%d")

    train["year"] = train["date"].dt.year
    train["quarter"] = "Q" + train["date"].dt.quarter.astype(str)
    quarterly_report = train.groupby(["year", "quarter"], as_index=False, observed=True).agg(
        unit_sales=("sales", "sum"), promotion_units=("onpromotion", "sum")
    )
    annual_report = train.groupby("year", as_index=False, observed=True).agg(
        unit_sales=("sales", "sum"), promotion_units=("onpromotion", "sum"), observed_days=("date", "nunique")
    )

    current_end = train["date"].max()
    current_start = pd.Timestamp(year=current_end.year, month=1, day=1)
    prior_start = current_start - pd.DateOffset(years=1)
    prior_end = current_end - pd.DateOffset(years=1)
    current_ytd = train[train["date"].between(current_start, current_end)]
    prior_ytd = train[train["date"].between(prior_start, prior_end)]

    def scorecard(current: pd.DataFrame, prior: pd.DataFrame, key: str) -> pd.DataFrame:
        current_agg = current.groupby(key, observed=True).agg(
            current_ytd_sales=("sales", "sum"), current_ytd_promotion_units=("onpromotion", "sum")
        )
        prior_agg = prior.groupby(key, observed=True).agg(prior_ytd_sales=("sales", "sum"))
        result = current_agg.join(prior_agg, how="left").reset_index()
        result["growth_yoy"] = result["current_ytd_sales"] / result["prior_ytd_sales"].replace(0, np.nan) - 1
        return result

    branch_scorecard = scorecard(current_ytd, prior_ytd, "store_nbr").merge(
        stores, on="store_nbr", how="left", validate="one_to_one"
    )
    family_scorecard = scorecard(current_ytd, prior_ytd, "family")

    def forecast_scorecard(key: str) -> pd.DataFrame:
        grouped = validation.groupby(key, observed=True).agg(
            actual_sales=("actual_sales", "sum"),
            forecast_sales=("forecast_sales", "sum"),
            absolute_error=("absolute_error", "sum"),
        ).reset_index()
        grouped["forecast_bias"] = (
            grouped["forecast_sales"] - grouped["actual_sales"]
        ) / grouped["actual_sales"].replace(0, np.nan)
        grouped["wape"] = grouped["absolute_error"] / grouped["actual_sales"].replace(0, np.nan)
        grouped["forecast_accuracy"] = (1 - grouped["wape"]).clip(lower=0)
        return grouped

    forecast_store = forecast_scorecard("store_nbr").merge(
        stores, on="store_nbr", how="left", validate="one_to_one"
    )
    forecast_family = forecast_scorecard("family")
    action_register = (
        validation.groupby(["store_nbr", "family"], observed=True)
        .agg(actual_sales=("actual_sales", "sum"), forecast_sales=("forecast_sales", "sum"), absolute_error=("absolute_error", "sum"))
        .reset_index()
    )
    action_register["forecast_bias"] = (
        action_register["forecast_sales"] - action_register["actual_sales"]
    ) / action_register["actual_sales"].replace(0, np.nan)
    action_register["wape"] = action_register["absolute_error"] / action_register["actual_sales"].replace(0, np.nan)
    action_register = action_register[action_register["actual_sales"] >= 100].nlargest(25, "absolute_error")
    action_register["priority"] = np.where(action_register["wape"] >= 0.5, "P1", "P2")
    action_register["recommended_action"] = np.where(
        action_register["forecast_bias"] < 0,
        "Review under-forecast and replenishment assumptions",
        "Review over-forecast and demand assumptions",
    )
    action_register["owner"] = "Inventory Planning"
    action_register["status"] = "Not Started"

    test_forecast = recursive_weekly_forecast(
        train[["date", "store_nbr", "family", "sales"]],
        test[["id", "date", "store_nbr", "family"]],
    )
    submission = test[["id"]].merge(
        test_forecast[["id", "forecast_sales"]], on="id", how="left", validate="one_to_one"
    ).rename(columns={"forecast_sales": "sales"})

    families = pd.DataFrame({"family": sorted(train["family"].astype(str).unique())})
    families.insert(0, "family_key", range(1, len(families) + 1))
    dim_date = build_date_dimension(train["date"].min(), test["date"].max())

    monthly.to_csv(processed_dir / "monthly_store_family.csv", index=False)
    daily_store.assign(date=daily_store["date"].dt.strftime("%Y-%m-%d")).to_csv(
        processed_dir / "daily_store_performance.csv", index=False
    )
    validation.assign(date=pd.to_datetime(validation["date"]).dt.strftime("%Y-%m-%d")).to_csv(
        processed_dir / "forecast_validation.csv", index=False
    )
    submission.to_csv(root / "submission.csv", index=False)
    monthly_report.to_csv(reporting_dir / "monthly_report.csv", index=False)
    quarterly_report.to_csv(reporting_dir / "quarterly_report.csv", index=False)
    annual_report.to_csv(reporting_dir / "annual_report.csv", index=False)
    branch_scorecard.to_csv(reporting_dir / "branch_scorecard.csv", index=False)
    family_scorecard.to_csv(reporting_dir / "family_scorecard.csv", index=False)
    forecast_store.to_csv(reporting_dir / "forecast_by_store.csv", index=False)
    forecast_family.to_csv(reporting_dir / "forecast_by_family.csv", index=False)
    action_register.to_csv(reporting_dir / "action_register.csv", index=False)
    driver_relationships.to_csv(reporting_dir / "driver_relationships.csv", index=False)

    stores.rename(columns={"type": "store_type"}).to_csv(powerbi_dir / "dim_store.csv", index=False)
    families.to_csv(powerbi_dir / "dim_family.csv", index=False)
    dim_date.to_csv(powerbi_dir / "dim_date.csv", index=False)
    monthly.to_csv(powerbi_dir / "fact_monthly_store_family.csv", index=False)
    daily_store.assign(date=daily_store["date"].dt.strftime("%Y-%m-%d")).to_csv(
        powerbi_dir / "fact_daily_store.csv", index=False
    )
    validation.assign(date=pd.to_datetime(validation["date"]).dt.strftime("%Y-%m-%d")).to_csv(
        powerbi_dir / "fact_forecast_validation.csv", index=False
    )

    database_path = root / "retail_demand.sqlite"
    with sqlite3.connect(database_path) as connection:
        stores.rename(columns={"type": "store_type"}).to_sql("dim_store", connection, if_exists="replace", index=False)
        families.to_sql("dim_family", connection, if_exists="replace", index=False)
        dim_date.to_sql("dim_date", connection, if_exists="replace", index=False)
        monthly.to_sql("fact_monthly_store_family", connection, if_exists="replace", index=False)
        validation.assign(date=pd.to_datetime(validation["date"]).dt.strftime("%Y-%m-%d")).to_sql(
            "fact_forecast_validation", connection, if_exists="replace", index=False
        )
        daily_store.assign(date=daily_store["date"].dt.strftime("%Y-%m-%d")).to_sql(
            "fact_daily_store", connection, if_exists="replace", index=False
        )

    summary = {
        "validation_start": validation_start.date().isoformat(),
        "validation_end": train["date"].max().date().isoformat(),
        "forecast_horizon_days": FORECAST_HORIZON,
        "validation_rows": int(len(validation)),
        "validation_rmsle": validation_score,
        "validation_bias": validation_bias,
        "validation_wape": validation_wape,
        "submission_rows": int(len(submission)),
        "submission_null_predictions": int(submission["sales"].isna().sum()),
        "submission_negative_predictions": int((submission["sales"] < 0).sum()),
    }
    (validation_dir / "model_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
