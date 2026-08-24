from __future__ import annotations

import json
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "analysis.ipynb"
REPORT = ROOT / "validation" / "notebook_validation.json"


def main() -> None:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    nbformat.validate(notebook)

    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    error_outputs = []
    missing_execution_counts = []

    for index, cell in enumerate(notebook.cells, start=1):
        if cell.cell_type != "code":
            continue
        if cell.execution_count is None:
            missing_execution_counts.append(index)
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                error_outputs.append(
                    {
                        "cell": index,
                        "ename": output.get("ename"),
                        "evalue": output.get("evalue"),
                    }
                )

    report = {
        "notebook": NOTEBOOK.name,
        "schema_valid": True,
        "code_cells": len(code_cells),
        "executed_code_cells": sum(cell.execution_count is not None for cell in code_cells),
        "missing_execution_count_cells": missing_execution_counts,
        "error_outputs": error_outputs,
        "status": "pass" if not missing_execution_counts and not error_outputs else "fail",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
