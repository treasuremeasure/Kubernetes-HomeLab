from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from datetime import date
from contextlib import asynccontextmanager

from db import init_db, close_db, insert_steps, get_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(lifespan=lifespan)


class StepData(BaseModel):
    date: date
    steps: int

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Steps must be non-negative")
        if v > 500_000:
            raise ValueError("Steps must not exceed 500 000")
        return v

    @field_validator("date")
    @classmethod
    def validate_date_not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Date must not be in the future")
        return v


@app.get("/healthz")
async def healthz():
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1;")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/api/v1/ingest", status_code=201)
async def ingest_steps(data: StepData):
    try:
        record = await insert_steps(data.date, data.steps)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {"status": "ok", "record": record}

