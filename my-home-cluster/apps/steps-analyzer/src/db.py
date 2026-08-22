import aiosqlite
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "steps.db"

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    return _db


async def init_db() -> None:
    global _db
    _db = await aiosqlite.connect(str(DB_PATH))
    _db.row_factory = aiosqlite.Row

    await _db.execute("PRAGMA journal_mode=WAL;")
    await _db.execute("PRAGMA foreign_keys=ON;")

    await _db.execute(
        """
        CREATE TABLE IF NOT EXISTS steps (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            date       TEXT    NOT NULL UNIQUE,
            steps      INTEGER NOT NULL CHECK (steps >= 0 AND steps <= 500000),
            created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );
        """
    )
    await _db.commit()


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None


async def insert_steps(step_date: date, steps: int) -> dict:
    db = await get_db()
    date_str = step_date.isoformat()
    created_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        cursor = await db.execute(
            "INSERT INTO steps (date, steps, created_at) VALUES (?, ?, ?)",
            (date_str, steps, created_at),
        )
        await db.commit()
    except aiosqlite.IntegrityError:
        raise ValueError(f"Record for date {date_str} already exists")

    return {
        "id": cursor.lastrowid,
        "date": date_str,
        "steps": steps,
        "created_at": created_at,
    }
