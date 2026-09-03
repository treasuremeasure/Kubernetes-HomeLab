CREATE TABLE IF NOT EXISTS steps (
    id         SERIAL PRIMARY KEY,
    date       DATE NOT NULL UNIQUE,
    steps      INTEGER NOT NULL CHECK (steps >= 0 AND steps <= 500000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_steps_date ON steps(date);
