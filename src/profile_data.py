"""Profile the Kaggle Store Sales source files without loading train.csv at once."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


EXPECTED_COLUMNS = {
    "train.csv": ["id", "date", "store_nbr", "family", "sales", "onpromotion"],
    "test.csv": ["id", "date", "store_nbr", "family", "onpromotion"],
    "stores.csv": ["store_nbr", "city", "state", "type", "cluster"],
    "transactions.csv": ["date", "store_nbr", "transactions"],
    "oil.csv": ["date", "dcoilwtico"],
    "holidays_events.csv": [
        "date",
        "type",
        "locale",
        "locale_name",
        "description",
        "transferred",
    ],
    "sample_submission.csv": ["id", "sales"],
}


def profile_small_csv(path: Path) -> dict:
    frame = pd.read_csv(path)
    result = {
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "nulls": {key: int(value) for key, value in frame.isna().sum().items()},
        "exact_duplicate_rows": int(frame.duplicated().sum()),
    }
    if "date" in frame.columns:
        dates = pd.to_datetime(frame["date"], errors="coerce")
        result["date_min"] = dates.min().date().isoformat()
        result["date_max"] = dates.max().date().isoformat()
        result["invalid_dates"] = int(dates.isna().sum())
    return result


def profile_train(path: Path, chunksize: int = 250_000) -> dict:
    rows = 0
    nulls: dict[str, int] = {}
    id_min = None
    id_max = None
    date_min = None
    date_max = None
    sales_negative = 0
    sales_zero = 0
    sales_total = 0.0
    onpromotion_negative = 0
    onpromotion_positive = 0
    stores: set[int] = set()
    families: set[str] = set()
    key_seen: set[int] = set()
    duplicate_ids = 0

    for chunk in pd.read_csv(path, chunksize=chunksize):
        rows += len(chunk)
        for column, value in chunk.isna().sum().items():
            nulls[column] = nulls.get(column, 0) + int(value)

        identifiers = chunk["id"].astype("int64")
        id_min = int(identifiers.min()) if id_min is None else min(id_min, int(identifiers.min()))
        id_max = int(identifiers.max()) if id_max is None else max(id_max, int(identifiers.max()))
        duplicate_ids += int(identifiers.isin(key_seen).sum())
        duplicate_ids += int(identifiers.duplicated().sum())
        key_seen.update(identifiers.unique().tolist())

        dates = pd.to_datetime(chunk["date"], errors="coerce")
        current_min = dates.min()
        current_max = dates.max()
        date_min = current_min if date_min is None else min(date_min, current_min)
        date_max = current_max if date_max is None else max(date_max, current_max)

        sales_negative += int((chunk["sales"] < 0).sum())
        sales_zero += int((chunk["sales"] == 0).sum())
        sales_total += float(chunk["sales"].sum())
        onpromotion_negative += int((chunk["onpromotion"] < 0).sum())
        onpromotion_positive += int((chunk["onpromotion"] > 0).sum())
        stores.update(chunk["store_nbr"].dropna().astype(int).unique().tolist())
        families.update(chunk["family"].dropna().astype(str).unique().tolist())

    return {
        "rows": int(rows),
        "columns": EXPECTED_COLUMNS["train.csv"],
        "nulls": nulls,
        "id_min": id_min,
        "id_max": id_max,
        "duplicate_ids": duplicate_ids,
        "date_min": date_min.date().isoformat(),
        "date_max": date_max.date().isoformat(),
        "distinct_stores": len(stores),
        "distinct_families": len(families),
        "negative_sales": sales_negative,
        "zero_sales": sales_zero,
        "zero_sales_rate": sales_zero / rows,
        "sales_total": sales_total,
        "negative_onpromotion": onpromotion_negative,
        "positive_onpromotion_rows": onpromotion_positive,
        "positive_onpromotion_rate": onpromotion_positive / rows,
    }


def validate_cross_file_integrity(data_dir: Path) -> dict:
    stores = pd.read_csv(data_dir / "stores.csv")
    store_ids = set(stores["store_nbr"].astype(int))
    train_store_ids: set[int] = set()
    train_families: set[str] = set()
    train_dates: set[str] = set()

    for chunk in pd.read_csv(
        data_dir / "train.csv",
        usecols=["date", "store_nbr", "family"],
        chunksize=250_000,
    ):
        train_store_ids.update(chunk["store_nbr"].astype(int).unique().tolist())
        train_families.update(chunk["family"].astype(str).unique().tolist())
        train_dates.update(chunk["date"].astype(str).unique().tolist())

    test = pd.read_csv(data_dir / "test.csv")
    transactions = pd.read_csv(data_dir / "transactions.csv")
    holidays = pd.read_csv(data_dir / "holidays_events.csv")
    oil = pd.read_csv(data_dir / "oil.csv")
    train_calendar = pd.date_range(min(train_dates), max(train_dates), freq="D")
    missing_train_dates = sorted(
        set(train_calendar.strftime("%Y-%m-%d")) - train_dates
    )

    return {
        "train_orphan_store_keys": sorted(train_store_ids - store_ids),
        "test_orphan_store_keys": sorted(set(test["store_nbr"].astype(int)) - store_ids),
        "transaction_orphan_store_keys": sorted(
            set(transactions["store_nbr"].astype(int)) - store_ids
        ),
        "train_family_count": len(train_families),
        "test_new_families": sorted(set(test["family"].astype(str)) - train_families),
        "train_distinct_dates": len(train_dates),
        "expected_train_calendar_days": int(
            (
                pd.Timestamp(max(train_dates)) - pd.Timestamp(min(train_dates))
            ).days
            + 1
        ),
        "missing_train_dates": missing_train_dates,
        "test_expected_grid_rows": int(
            test["date"].nunique()
            * test["store_nbr"].nunique()
            * test["family"].nunique()
        ),
        "test_actual_rows": int(len(test)),
        "transaction_duplicate_date_store_keys": int(
            transactions.duplicated(["date", "store_nbr"]).sum()
        ),
        "holiday_dates_with_multiple_records": int(
            (holidays.groupby("date").size() > 1).sum()
        ),
        "oil_missing_value_rate": float(oil["dcoilwtico"].isna().mean()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    report = {
        "source": "Kaggle Store Sales - Time Series Forecasting",
        "data_directory": str(data_dir),
        "files": {},
    }

    for filename, expected in EXPECTED_COLUMNS.items():
        path = data_dir / filename
        if not path.exists():
            report["files"][filename] = {"missing_file": True}
            continue
        columns = list(pd.read_csv(path, nrows=0).columns)
        file_report = profile_train(path) if filename == "train.csv" else profile_small_csv(path)
        file_report["schema_matches_expected"] = columns == expected
        report["files"][filename] = file_report

    report["integrity"] = validate_cross_file_integrity(data_dir)
    output_text = json.dumps(report, indent=2, ensure_ascii=False)
    print(output_text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
