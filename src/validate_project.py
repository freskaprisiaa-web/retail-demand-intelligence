from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "validation" / "project_validation.json"
SUMMARY_PATH = ROOT / "validation" / "VALIDATION_SUMMARY.md"


def check(name: str, condition: bool, detail: str) -> dict[str, object]:
    return {"check": name, "status": "pass" if condition else "fail", "detail": detail}


def main() -> None:
    results: list[dict[str, object]] = []

    with (ROOT / "validation" / "source_profile.json").open(encoding="utf-8") as handle:
        profile = json.load(handle)
    with (ROOT / "validation" / "model_summary.json").open(encoding="utf-8") as handle:
        model = json.load(handle)
    with (ROOT / "validation" / "notebook_validation.json").open(encoding="utf-8") as handle:
        notebook = json.load(handle)

    results.append(check("Source row count", profile["files"]["train.csv"]["rows"] == 3_000_888, "3,000,888 training rows"))
    results.append(check("Source primary key", profile["files"]["train.csv"]["duplicate_ids"] == 0, "No duplicate training IDs"))
    results.append(check("Notebook execution", notebook["status"] == "pass", f"{notebook['executed_code_cells']} code cells executed without error"))

    submission = pd.read_csv(ROOT / "submission.csv")
    submission_ok = (
        list(submission.columns) == ["id", "sales"]
        and len(submission) == 28_512
        and submission["id"].is_unique
        and submission["sales"].notna().all()
        and submission["sales"].ge(0).all()
    )
    results.append(check("Kaggle submission", submission_ok, "28,512 unique id,sales rows; no null or negative predictions"))
    results.append(check("Forecast metric reconciliation", abs(model["validation_rmsle"] - 0.5510361765498359) < 1e-12, f"RMSLE {model['validation_rmsle']:.6f}"))

    daily = pd.read_csv(ROOT / "data" / "powerbi" / "fact_daily_store.csv")
    integrated_columns = {"transactions", "oil_price_wti", "oil_price_was_missing", "is_holiday", "holiday_event_count"}
    results.append(check("Multi-source BI integration", integrated_columns.issubset(daily.columns), "Transactions, oil, and locale-aware holiday fields are present"))
    results.append(check("Daily-store grain", not daily.duplicated(["date", "store_nbr"]).any(), f"{len(daily):,} unique date-store rows"))

    drivers = pd.read_csv(ROOT / "data" / "reporting" / "driver_relationships.csv")
    results.append(check("Driver diagnostics", len(drivers) == 4 and drivers["value"].notna().all(), "Four descriptive demand-driver relationships"))

    with sqlite3.connect(ROOT / "retail_demand.sqlite") as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required_tables = {"dim_store", "dim_family", "dim_date", "fact_monthly_store_family", "fact_daily_store", "fact_forecast_validation"}
        results.append(check("SQLite analytical model", required_tables.issubset(tables), ", ".join(sorted(required_tables))))

    dashboard_text = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    dashboard_ok = "__DATA__" not in dashboard_text and "month_start" in dashboard_text and "Retail Demand Intelligence" in dashboard_text
    results.append(check("Portable dashboard", dashboard_ok, "Self-contained HTML with embedded data and corrected month field"))

    workbook_path = ROOT / "Retail_Demand_Intelligence.xlsx"
    workbook_sheets: list[str] = []
    workbook_ok = False
    if zipfile.is_zipfile(workbook_path):
        with zipfile.ZipFile(workbook_path) as archive:
            workbook_xml = ElementTree.fromstring(archive.read("xl/workbook.xml"))
            ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            workbook_sheets = [sheet.attrib["name"] for sheet in workbook_xml.findall("m:sheets/m:sheet", ns)]
            bad_tokens = ("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A")
            xml_text = "".join(
                archive.read(name).decode("utf-8", errors="ignore")
                for name in archive.namelist()
                if name.endswith(".xml")
            )
            workbook_ok = not any(token in xml_text for token in bad_tokens)
    required_sheets = {"Executive Summary", "Monthly Report", "Quarterly Report", "Annual Report", "Branch Scorecard", "Forecast Monitoring", "Action Register", "Driver Diagnostics"}
    results.append(check("Excel management pack", workbook_ok and required_sheets.issubset(workbook_sheets), f"{len(workbook_sheets)} sheets; no stored formula-error tokens"))

    powerbi_files = list((ROOT / "data" / "powerbi").glob("*.csv"))
    powerbi_ok = len(powerbi_files) >= 6 and (ROOT / "powerbi" / "dax_measures.dax").exists() and (ROOT / "powerbi" / "POWER_BI_BUILD_GUIDE.md").exists()
    results.append(check("Power BI handoff", powerbi_ok, f"{len(powerbi_files)} model CSVs plus DAX and build guide"))

    overall = "pass" if all(result["status"] == "pass" for result in results) else "fail"
    report = {"status": overall, "checks": results}
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = ["# Validation Summary", "", f"**Overall status:** {overall.upper()}", ""]
    lines.extend(
        f"- [{'x' if result['status'] == 'pass' else ' '}] **{result['check']}** — {result['detail']}"
        for result in results
    )
    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if overall != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
