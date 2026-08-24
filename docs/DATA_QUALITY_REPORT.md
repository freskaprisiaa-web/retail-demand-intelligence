# Data Quality Assessment

## Dataset and grain

- `train.csv`: one row per date × store × product family; 3,000,888 rows.
- `test.csv`: the same feature grain for a 16-day prediction horizon; 28,512 rows.
- Store, transaction, oil, and holiday/event files enrich the core fact data at their documented grains.

## Findings

| Finding | Evidence | Risk / handling | Severity |
|---|---|---|---|
| Core train schema and IDs valid | Required columns match; 0 duplicate IDs; 0 nulls | Safe primary analytical grain | Pass |
| Store integrity valid | 54 stores; no orphan store keys in train, test, or transactions | Dimension joins are safe | Pass |
| Four absent calendar dates | 25 Dec in 2013–2016 is absent from train | Treat as source calendar closure, not zero-demand records | Low |
| Oil price missingness | 43 of 1,218 values (3.53%) are null | Forward-fill then back-fill only within the observed series; retain imputation flag | Medium |
| Holiday dates can repeat | 31 dates have multiple event rows | Aggregate event attributes before joining to avoid fact-row multiplication | High if untreated |
| Zero-sales observations | 939,130 rows (31.30%) | Valid sparse demand; use log metric and segment zero-demand behavior | Expected |
| Test grid complete | 16 × 54 × 33 = 28,512 rows | One prediction can be generated for every required ID | Pass |

The machine-readable evidence is saved in `validation/source_profile.json` and can be regenerated with `src/profile_data.py`.

