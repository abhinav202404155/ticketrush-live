"""booking-service: accepts booking REQUESTS and puts them in a queue.
It does not touch seats itself; the worker does that (one at a time, safely).
Flow: QUEUED -> (worker) HELD for 5 min -> (mock pay) CONFIRMED. Or FAILED / EXPIRED."""
import hmac
import json
import os
import urllib.parse
import urllib.request
from contextlib import asynccontextmanager

import jwt
import pika
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from . import observability
from .db import pool

JWT_SECRET = os.environ["JWT_SECRET"]
ADMIN_KEY = os.environ["ADMIN_KEY"]
RABBIT_URL = os.environ["RABBITMQ_URL"]
QUEUE = "booking_requests"
PROM_URL = os.getenv("PROMETHEUS_URL", "")  # empty under docker-compose, set in Kubernetes
BOOKING_LIMIT = os.getenv("BOOKING_RATE_LIMIT", "30/minute")
DASHBOARD_LIMIT = os.getenv("DASHBOARD_RATE_LIMIT", "120/minute")
# "true" = the dashboard needs no key. It exposes only aggregate numbers (no emails, no booking details).
DASHBOARD_PUBLIC = os.getenv("DASHBOARD_PUBLIC", "false").lower() == "true"

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open(wait=True, timeout=30)
    yield
    pool.close()


app = FastAPI(title="TicketRush booking-service", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
Instrumentator().instrument(app).expose(app)


class BookingIn(BaseModel):
    show_id: int
    seat_ids: list[int] = Field(min_length=1, max_length=6)


class PaymentIn(BaseModel):
    card_number: str = Field(min_length=4, max_length=19)  # MOCK. A card ending 0000 is declined.


def current_user_id(authorization: str) -> int:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        return int(jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])["sub"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def publish(booking_id: int) -> None:
    """Put one message on the queue. (New connection per call: simple, fine for a demo.)"""
    connection = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
    try:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE, durable=True)  # durable: survives broker restart
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE,
            body=json.dumps({"booking_id": booking_id}),
            properties=pika.BasicProperties(delivery_mode=2),  # persist message to disk
        )
    finally:
        connection.close()


def queue_position(conn, booking_id: int):
    """Number of QUEUED bookings at or ahead of this one (ids grow in arrival order)."""
    return conn.execute(
        "SELECT COUNT(*) AS n FROM bookings WHERE status = 'QUEUED' AND id <= %s", (booking_id,)
    ).fetchone()["n"]


def booking_view(conn, b) -> dict:
    labels = conn.execute(
        "SELECT label FROM seats WHERE id = ANY(%s) ORDER BY id", (b["seat_ids"],)
    ).fetchall()
    return {
        "booking_id": b["id"],
        "show_id": b["show_id"],
        "status": b["status"],
        "reason": b["reason"],
        "seats": [r["label"] for r in labels],
        "expires_at": b["expires_at"],
        "queue_position": queue_position(conn, b["id"]) if b["status"] == "QUEUED" else None,
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/api/bookings", status_code=202)  # 202 = "accepted, still processing"
@limiter.limit(BOOKING_LIMIT)
def create_booking(request: Request, body: BookingIn, authorization: str = Header(default="")):
    user_id = current_user_id(authorization)
    with pool.connection() as conn:
        show = conn.execute(
            "SELECT (opens_at <= now()) AS is_open FROM shows WHERE id = %s", (body.show_id,)
        ).fetchone()
        if not show:
            raise HTTPException(status_code=404, detail="Show not found")
        if not show["is_open"]:
            raise HTTPException(status_code=403, detail="Booking has not opened yet")
        booking_id = conn.execute(
            "INSERT INTO bookings (user_id, show_id, seat_ids, status) VALUES (%s, %s, %s, 'QUEUED') RETURNING id",
            (user_id, body.show_id, sorted(set(body.seat_ids))),
        ).fetchone()["id"]
    # The row is committed BEFORE we publish, so the worker always finds it.
    try:
        publish(booking_id)
    except Exception:
        with pool.connection() as conn:
            conn.execute(
                "UPDATE bookings SET status = 'FAILED', reason = 'Queue unavailable' WHERE id = %s", (booking_id,)
            )
        raise HTTPException(status_code=503, detail="Queue unavailable, please retry")
    with pool.connection() as conn:
        return {"booking_id": booking_id, "status": "QUEUED", "queue_position": queue_position(conn, booking_id)}


@app.get("/api/bookings/mine")
def my_bookings(authorization: str = Header(default="")):
    user_id = current_user_id(authorization)
    with pool.connection() as conn:
        conn.execute(
            "UPDATE bookings SET status = 'EXPIRED' WHERE user_id = %s AND status = 'HELD' AND expires_at < now()",
            (user_id,),
        )
        rows = conn.execute(
            "SELECT * FROM bookings WHERE user_id = %s ORDER BY id DESC LIMIT 50", (user_id,)
        ).fetchall()
        return [booking_view(conn, b) for b in rows]


@app.get("/api/bookings/{booking_id}")
def get_booking(booking_id: int, authorization: str = Header(default="")):
    user_id = current_user_id(authorization)
    with pool.connection() as conn:
        conn.execute(
            "UPDATE bookings SET status = 'EXPIRED' WHERE id = %s AND status = 'HELD' AND expires_at < now()",
            (booking_id,),
        )
        b = conn.execute("SELECT * FROM bookings WHERE id = %s AND user_id = %s", (booking_id, user_id)).fetchone()
        if not b:
            raise HTTPException(status_code=404, detail="Booking not found")
        return booking_view(conn, b)


@app.post("/api/bookings/{booking_id}/pay")
def pay(booking_id: int, body: PaymentIn, authorization: str = Header(default="")):
    """MOCK payment. No money moves. Seats go HELD -> SOLD only if our hold is still valid."""
    user_id = current_user_id(authorization)
    outcome = None  # decided inside the transaction, raised after it (raising would roll back)
    with pool.connection() as conn:
        b = conn.execute(
            "SELECT *, (expires_at < now()) AS expired FROM bookings WHERE id = %s AND user_id = %s FOR UPDATE",
            (booking_id, user_id),
        ).fetchone()
        if not b:
            raise HTTPException(status_code=404, detail="Booking not found")
        if b["status"] == "CONFIRMED":
            return booking_view(conn, b)
        if b["status"] != "HELD":
            raise HTTPException(status_code=409, detail=f"Booking is {b['status']}, cannot pay")
        if body.card_number.endswith("0000"):
            outcome = (402, "Payment declined (mock card ending 0000)")
        else:
            # Lock our seats in id order (same order as the worker, so no deadlocks).
            mine = conn.execute(
                "SELECT id FROM seats WHERE booking_id = %s AND status = 'HELD' AND held_until > now() "
                "ORDER BY id FOR UPDATE",
                (booking_id,),
            ).fetchall()
            if b["expired"] or len(mine) != len(b["seat_ids"]):
                conn.execute("UPDATE bookings SET status = 'EXPIRED' WHERE id = %s", (booking_id,))
                outcome = (410, "Your 5-minute hold expired")
            else:
                conn.execute(
                    "UPDATE seats SET status = 'SOLD', held_until = NULL WHERE booking_id = %s AND id = ANY(%s)",
                    (booking_id, b["seat_ids"]),
                )
                conn.execute("UPDATE bookings SET status = 'CONFIRMED' WHERE id = %s", (booking_id,))
    if outcome:
        raise HTTPException(status_code=outcome[0], detail=outcome[1])
    with pool.connection() as conn:
        b = conn.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,)).fetchone()
        return booking_view(conn, b)


def require_admin(key: str) -> None:
    """Constant-time comparison, so response timing cannot be used to guess the key."""
    if not hmac.compare_digest(key.encode(), ADMIN_KEY.encode()):
        raise HTTPException(status_code=401, detail="Bad admin key")


def running_pods():
    """How many pods of each service are up, from Prometheus. None if Prometheus is not available."""
    if not PROM_URL:
        return None
    try:
        q = urllib.parse.quote('count by (app) (up{job="ticketrush-apps"} == 1)')
        with urllib.request.urlopen(f"{PROM_URL}/api/v1/query?query={q}", timeout=1.5) as r:
            data = json.load(r)
        return {x["metric"]["app"]: int(x["value"][1]) for x in data["data"]["result"]}
    except Exception:
        return None


@app.get("/api/admin/stats")
def admin_stats(x_admin_key: str = Header(default="")):
    """Numbers for the Control Room page."""
    require_admin(x_admin_key)
    with pool.connection() as conn:
        rows = conn.execute("SELECT status, COUNT(*) AS n FROM bookings GROUP BY status").fetchall()
        sold = conn.execute("SELECT COUNT(*) AS n FROM seats WHERE status = 'SOLD'").fetchone()["n"]
    counts = {r["status"]: r["n"] for r in rows}
    accepted = counts.get("HELD", 0) + counts.get("CONFIRMED", 0) + counts.get("EXPIRED", 0)
    processed = accepted + counts.get("FAILED", 0)
    return {
        "queue_length": counts.get("QUEUED", 0),
        "counts": counts,
        "seats_sold": sold,
        "pods": running_pods(),
        "success_rate": round(accepted / processed * 100, 1) if processed else None,
    }


@app.get("/api/admin/overview")
@limiter.limit(DASHBOARD_LIMIT)
def admin_overview(request: Request, window: int = 30, x_admin_key: str = Header(default="")):
    """Everything the Control Room dashboard shows, in one response (see observability.py)."""
    if not DASHBOARD_PUBLIC:
        require_admin(x_admin_key)
    return observability.build_overview(pool, RABBIT_URL, window)
