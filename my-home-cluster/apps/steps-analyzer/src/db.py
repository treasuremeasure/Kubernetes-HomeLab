import os

import asyncpg
from datetime import date

_pool: asyncpg.Pool | None = None

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "steps-postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "steps_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "steps_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "steps_password")
DATABASE_URL = os.getenv("DATABASE_URL")


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        raise RuntimeError("Database pool not initialised. Call init_db() first.")
    return _pool


async def init_db() -> None:
    global _pool
    if DATABASE_URL:
        _pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=10)
    else:
        _pool = await asyncpg.create_pool(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            min_size=1,
            max_size=10,
        )

    async with _pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS steps (
                id         SERIAL PRIMARY KEY,
                date       DATE NOT NULL UNIQUE,
                steps      INTEGER NOT NULL CHECK (steps >= 0 AND steps <= 500000),
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


async def close_db() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def insert_steps(step_date: date, steps: int) -> dict:
    pool = await get_pool()
    date_str = step_date.isoformat()

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO steps (date, steps)
                VALUES ($1, $2)
                RETURNING id, date, steps, created_at;
                """,
                step_date,
                steps,
            )
    except asyncpg.UniqueViolationError:
        raise ValueError(f"Record for date {date_str} already exists")

    return {
        "id": row["id"],
        "date": row["date"].isoformat(),
        "steps": row["steps"],
        "created_at": row["created_at"].isoformat(),
    }

