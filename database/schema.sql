CREATE TABLE IF NOT EXISTS wanted_criminals (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(120),
    nickname VARCHAR(120) NOT NULL CHECK (length(trim(nickname)) > 0),
    reward NUMERIC(14, 2) NOT NULL CHECK (reward BETWEEN 0 AND 999999999999.99),
    latitude NUMERIC(9, 6) CHECK (latitude BETWEEN -90 AND 90),
    longitude NUMERIC(9, 6) CHECK (longitude BETWEEN -180 AND 180),
    location_note TEXT,
    difficulty SMALLINT NOT NULL CHECK (difficulty BETWEEN 1 AND 10),
    armed BOOLEAN NOT NULL DEFAULT FALSE,
    has_crew BOOLEAN NOT NULL DEFAULT FALSE,
    escape_master BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT valid_location CHECK (
        (latitude IS NOT NULL AND longitude IS NOT NULL)
        OR (latitude IS NULL AND longitude IS NULL AND length(trim(location_note)) > 0 AND location_note IS NOT NULL)
    ),
    CONSTRAINT coordinate_pair CHECK ((latitude IS NULL) = (longitude IS NULL))
);

CREATE TABLE IF NOT EXISTS hunt_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    criminal_id BIGINT NOT NULL REFERENCES wanted_criminals(id) ON DELETE RESTRICT,
    success BOOLEAN NOT NULL,
    notes TEXT NOT NULL CHECK (length(trim(notes)) BETWEEN 1 AND 10000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS hunt_logs_criminal_id_idx ON hunt_logs(criminal_id);
CREATE INDEX IF NOT EXISTS wanted_criminals_reward_idx ON wanted_criminals(reward);
CREATE TABLE IF NOT EXISTS app_metadata (key TEXT PRIMARY KEY);
