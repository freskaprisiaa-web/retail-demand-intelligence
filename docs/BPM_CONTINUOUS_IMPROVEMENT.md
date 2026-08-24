# Business Process Management & Continuous Improvement

## AS-IS process

1. Separate files are reviewed independently.
2. Period totals are assembled manually.
3. Forecasts are produced without a shared exception threshold.
4. Follow-up actions are recorded inconsistently.
5. Forecast outcomes are not systematically fed back into the next cycle.

## TO-BE process

1. **Ingest** all sources using a controlled folder and schema checks.
2. **Validate** completeness, uniqueness, integrity, and temporal coverage.
3. **Transform** into reusable date, store, family, performance, and forecast tables.
4. **Analyze** KPI trends and exception segments.
5. **Forecast** using leakage-safe rolling validation.
6. **Decide** actions using severity, owner, due date, and expected impact.
7. **Monitor** RMSLE, bias, WAPE, and action completion monthly.
8. **Improve** features, thresholds, or process steps based on measured results.

## Improvement backlog

| Priority | Trigger | Action | Owner role | Success measure |
|---|---|---|---|---|
| P1 | High under-forecast bias | Review replenishment parameters for the affected store-family | Inventory planning | Bias approaches zero next cycle |
| P1 | Persistent zero sales with positive promotion | Validate availability, assortment, and promotion execution | Store operations | Fewer repeated exceptions |
| P2 | Volatile family with weak forecast accuracy | Add event/promotion features or segmented model | Data analyst | Lower validation RMSLE/WAPE |
| P2 | Missing/late external data | Add freshness alert and documented fallback | Data/IT | Refresh succeeds within SLA |
| P3 | Stable low-error segment | Reduce manual review frequency | Retail management | Analyst time saved without accuracy loss |

