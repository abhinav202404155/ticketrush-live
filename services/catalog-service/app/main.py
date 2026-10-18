"""catalog-service: read-only. Events (search/filter), their sessions, and seat maps."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .db import pool

# A HELD seat whose hold time has passed is really free again, so we treat it as AVAILABLE.
FREE = "(st.status = 'AVAILABLE' OR (st.status = 'HELD' AND st.held_until < now()))"


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


@app.get("/api/cities")
def cities():
    with pool.connection() as conn:
        return [r["city"] for r in conn.execute("SELECT DISTINCT city FROM shows ORDER BY city").fetchall()]


@app.get("/api/events")
def list_events(city: str = "", category: str = "", q: str = ""):
    """Search: matches title, genre, category, language or venue. Empty filters are ignored."""
    p = {"city": city or None, "cat": category or None, "like": f"%{q.strip()}%" if q.strip() else None}
    with pool.connection() as conn:
        return conn.execute(
            """
            SELECT e.id, e.title, e.category, e.language, e.genre, e.duration_min, e.rating, e.age_rating,
                   e.description, e.image_url, e.featured,
                   MIN(s.price_inr) AS from_price, MIN(s.opens_at) AS opens_at, MIN(s.starts_at) AS next_show
            FROM events e JOIN shows s ON s.event_id = e.id
            WHERE s.starts_at > now()
              AND (%(city)s::text IS NULL OR s.city = %(city)s::text)
              AND (%(cat)s::text IS NULL OR e.category = %(cat)s::text)
              AND (%(like)s::text IS NULL OR e.title ILIKE %(like)s::text OR e.genre ILIKE %(like)s::text
                   OR e.category ILIKE %(like)s::text OR e.language ILIKE %(like)s::text OR s.venue ILIKE %(like)s::text)
            GROUP BY e.id ORDER BY e.featured DESC, e.rating DESC, e.id
            """,
            p,
        ).fetchall()


@app.get("/api/events/{event_id}")
def get_event(event_id: int, city: str = ""):
    with pool.connection() as conn:
        e = conn.execute("SELECT * FROM events WHERE id = %s", (event_id,)).fetchone()
        if not e:
            raise HTTPException(status_code=404, detail="Event not found")
        sessions = conn.execute(
            f"""
            SELECT s.id, s.venue, s.city, s.starts_at, s.opens_at, s.price_inr, (s.opens_at <= now()) AS is_open,
                   COUNT(st.id) FILTER (WHERE {FREE}) AS seats_available
            FROM shows s LEFT JOIN seats st ON st.show_id = s.id
            WHERE s.event_id = %(id)s AND s.starts_at > now() AND (%(city)s::text IS NULL OR s.city = %(city)s::text)
            GROUP BY s.id ORDER BY s.starts_at
            """,
            {"id": event_id, "city": city or None},
        ).fetchall()
    return {**e, "sessions": sessions}


@app.get("/api/shows/{show_id}")
def get_show(show_id: int):
    """One session (used by the seat page), joined with its event."""
    with pool.connection() as conn:
        show = conn.execute(
            """SELECT s.id, s.event_id, s.venue, s.city, s.starts_at, s.opens_at, s.price_inr,
                      (s.opens_at <= now()) AS is_open, e.title, e.category, e.image_url
               FROM shows s JOIN events e ON e.id = s.event_id WHERE s.id = %s""",
            (show_id,),
        ).fetchone()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    return show


@app.get("/api/shows/{show_id}/seats")
def list_seats(show_id: int):
    with pool.connection() as conn:
        return conn.execute(
            "SELECT id, label, CASE WHEN status = 'HELD' AND held_until < now() THEN 'AVAILABLE' ELSE status END AS status "
            "FROM seats WHERE show_id = %s ORDER BY id",
            (show_id,),
        ).fetchall()
