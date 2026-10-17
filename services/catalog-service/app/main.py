"""catalog-service: read-only list of shows and their seat maps."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .db import pool

# A HELD seat whose hold time has passed is really free again, so we treat it as AVAILABLE.
EFFECTIVE_STATUS = """
CASE WHEN status = 'HELD' AND held_until < now() THEN 'AVAILABLE' ELSE status END
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open(wait=True, timeout=30)
    yield
    pool.close()


app = FastAPI(title="TicketRush catalog-service", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])
Instrumentator().instrument(app).expose(app)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/api/shows")
def list_shows():
    with pool.connection() as conn:
        return conn.execute(
            """
            SELECT s.id, s.title, s.venue, s.description, s.starts_at, s.opens_at, s.price_inr,
                   (s.opens_at <= now()) AS is_open,
                   COUNT(st.id) FILTER (
                     WHERE st.status = 'AVAILABLE' OR (st.status = 'HELD' AND st.held_until < now())
                   ) AS seats_available
            FROM shows s LEFT JOIN seats st ON st.show_id = s.id
            GROUP BY s.id ORDER BY s.starts_at
            """
        ).fetchall()


@app.get("/api/shows/{show_id}")
def get_show(show_id: int):
    with pool.connection() as conn:
        show = conn.execute(
            "SELECT id, title, venue, description, starts_at, opens_at, price_inr, "
            "(opens_at <= now()) AS is_open FROM shows WHERE id = %s",
            (show_id,),
        ).fetchone()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    return show


@app.get("/api/shows/{show_id}/seats")
def list_seats(show_id: int):
    with pool.connection() as conn:
        return conn.execute(
            f"SELECT id, label, {EFFECTIVE_STATUS} AS status FROM seats WHERE show_id = %s ORDER BY id",
            (show_id,),
        ).fetchall()
