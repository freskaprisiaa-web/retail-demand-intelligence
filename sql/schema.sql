PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dim_store (
    store_nbr INTEGER PRIMARY KEY,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    store_type TEXT NOT NULL,
    cluster INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_family (
    family_key INTEGER PRIMARY KEY,
    family TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date TEXT NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter TEXT NOT NULL,
    month_number INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    week_of_year INTEGER NOT NULL,
    day_name TEXT NOT NULL,
    is_weekend INTEGER NOT NULL,
    is_payday INTEGER NOT NULL,
    month_start TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_monthly_store_family (
    month_start TEXT NOT NULL,
    store_nbr INTEGER NOT NULL,
    family TEXT NOT NULL,
    unit_sales REAL NOT NULL,
    promotion_units INTEGER NOT NULL,
    observed_days INTEGER NOT NULL,
    PRIMARY KEY (month_start, store_nbr, family),
    FOREIGN KEY (store_nbr) REFERENCES dim_store(store_nbr)
);

CREATE TABLE IF NOT EXISTS fact_forecast_validation (
    date TEXT NOT NULL,
    store_nbr INTEGER NOT NULL,
    family TEXT NOT NULL,
    actual_sales REAL NOT NULL,
    forecast_sales REAL NOT NULL,
    absolute_error REAL NOT NULL,
    absolute_percentage_error REAL NOT NULL,
    PRIMARY KEY (date, store_nbr, family)
);

CREATE TABLE IF NOT EXISTS fact_daily_store (
    date TEXT NOT NULL,
    store_nbr INTEGER NOT NULL,
    unit_sales REAL NOT NULL,
    promotion_units INTEGER NOT NULL,
    transactions INTEGER,
    oil_price_wti REAL,
    oil_price_was_missing INTEGER NOT NULL,
    holiday_event_count INTEGER NOT NULL,
    holiday_descriptions TEXT NOT NULL,
    is_holiday INTEGER NOT NULL,
    units_per_transaction REAL,
    PRIMARY KEY (date, store_nbr),
    FOREIGN KEY (store_nbr) REFERENCES dim_store(store_nbr)
);

CREATE INDEX IF NOT EXISTS idx_monthly_store_family_month
ON fact_monthly_store_family(month_start);

CREATE INDEX IF NOT EXISTS idx_forecast_validation_segment
ON fact_forecast_validation(store_nbr, family);

CREATE INDEX IF NOT EXISTS idx_daily_store_date
ON fact_daily_store(date, store_nbr);
