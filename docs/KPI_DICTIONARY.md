# KPI Dictionary

No fabricated sales or inventory targets are introduced. Comparative KPIs use observed history, forecast error, growth, mix, and promotion behavior.

| KPI | Definition | Grain / use |
|---|---|---|
| Unit Sales | Sum of `sales` | Day, month, store, family |
| Transactions | Sum of store-level `transactions` | Day/month and store |
| Units per Transaction | Unit Sales / Transactions | Store and period productivity proxy |
| Sales Growth MoM | Current month sales / prior month sales - 1 | Momentum |
| Sales Growth YoY | Current month sales / same month prior year - 1 | Seasonally aligned growth |
| Promotion Penetration | Rows with `onpromotion > 0` / observed rows | Promotion exposure |
| Promotion Lift | Average sales on promoted rows / non-promoted rows - 1 | Descriptive association, not causal effect |
| Demand Volatility | Standard deviation / mean of daily sales | Planning stability |
| Forecast RMSLE | Root mean squared difference of `log1p(prediction)` and `log1p(actual)` | Competition metric |
| Forecast Bias | Sum(prediction - actual) / Sum(actual) | Over/under-forecast direction |
| Forecast Accuracy | 1 - WAPE, bounded at 0 | Management-friendly monitoring |
| Absolute Percentage Error | `abs(prediction-actual) / max(actual,1)` | Exception ranking |

## Guardrails

- Interpret promotion lift as association because promotions are not randomly assigned.
- Use RMSLE for Kaggle comparability and WAPE/bias for operational interpretation.
- Do not compare incomplete 2017 totals directly with full prior years; use aligned YTD or like-for-like periods.
- Review zero-sales groups separately because log metrics and percentage errors behave differently near zero.

