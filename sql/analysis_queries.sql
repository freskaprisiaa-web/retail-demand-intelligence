-- 1. Monthly performance with month-over-month growth.
WITH monthly AS (
    SELECT month_start, SUM(unit_sales) AS unit_sales
    FROM fact_monthly_store_family
    GROUP BY month_start
), compared AS (
    SELECT
        month_start,
        unit_sales,
        LAG(unit_sales) OVER (ORDER BY month_start) AS prior_month_sales
    FROM monthly
)
SELECT
    month_start,
    unit_sales,
    prior_month_sales,
    unit_sales / NULLIF(prior_month_sales, 0) - 1 AS growth_mom
FROM compared
ORDER BY month_start;

-- 2. Store-family forecast exceptions ranked by absolute error.
SELECT
    store_nbr,
    family,
    SUM(actual_sales) AS actual_sales,
    SUM(forecast_sales) AS forecast_sales,
    SUM(forecast_sales - actual_sales) / NULLIF(SUM(actual_sales), 0) AS forecast_bias,
    SUM(absolute_error) / NULLIF(SUM(actual_sales), 0) AS wape
FROM fact_forecast_validation
GROUP BY store_nbr, family
HAVING SUM(actual_sales) > 0
ORDER BY wape DESC
LIMIT 25;

-- 3. Promotion exposure by family.
SELECT
    family,
    SUM(promotion_units) AS promotion_units,
    SUM(unit_sales) AS unit_sales,
    SUM(promotion_units) / NULLIF(SUM(observed_days), 0) AS promotions_per_observed_day
FROM fact_monthly_store_family
GROUP BY family
ORDER BY promotion_units DESC;

-- 4. Descriptive demand-driver diagnostics (associations, not causal effects).
SELECT
    is_holiday,
    COUNT(*) AS store_days,
    AVG(unit_sales) AS average_unit_sales,
    AVG(transactions) AS average_transactions,
    AVG(oil_price_wti) AS average_oil_price,
    AVG(promotion_units) AS average_promotion_units
FROM fact_daily_store
GROUP BY is_holiday
ORDER BY is_holiday;
