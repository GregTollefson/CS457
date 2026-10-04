-- Initial schema for the FRED energy data project.

CREATE TABLE IF NOT EXISTS series (
    series_id VARCHAR(50) PRIMARY KEY,
    title TEXT NOT NULL,
    frequency VARCHAR(50),
    units VARCHAR(100),
    seasonal_adjustment VARCHAR(100),
    observation_start DATE,
    observation_end DATE,
    last_updated TIMESTAMPTZ,
    popularity INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS observations (
    series_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    value DOUBLE PRECISION,
    realtime_start DATE,
    realtime_end DATE,

    PRIMARY KEY (series_id, date),

    FOREIGN KEY (series_id)
        REFERENCES series(series_id)
        ON DELETE CASCADE
);