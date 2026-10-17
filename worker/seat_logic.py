"""The heart of TicketRush: grab seats so the same seat can NEVER be sold twice.

How it stays safe: SELECT ... FOR UPDATE locks the seat rows. If two workers want the
same seat, the second one WAITS until the first commits, then sees the seat is taken.
Rows are always locked in id order, so two workers can never deadlock each other."""
import os

from .db import pool

HOLD_SECONDS = int(os.getenv("HOLD_SECONDS", "300"))


def process_booking(booking_id: int) -> str:
    """Returns 'HELD', 'FAILED' or 'SKIPPED'."""
    with pool.connection() as conn:  # one transaction
        b = conn.execute(
            "SELECT id, show_id, seat_ids, status FROM bookings WHERE id = %s FOR UPDATE", (booking_id,)
        ).fetchone()
        if b is None or b["status"] != "QUEUED":
            return "SKIPPED"  # duplicate message or already handled

        seats = conn.execute(
            "SELECT id, status, (held_until < now()) AS hold_expired FROM seats "
            "WHERE show_id = %s AND id = ANY(%s) ORDER BY id FOR UPDATE",
            (b["show_id"], b["seat_ids"]),
        ).fetchall()

        all_free = len(seats) == len(b["seat_ids"]) and all(
            s["status"] == "AVAILABLE" or (s["status"] == "HELD" and s["hold_expired"]) for s in seats
        )
        if not all_free:
            conn.execute(
                "UPDATE bookings SET status = 'FAILED', reason = %s WHERE id = %s",
                ("One or more seats are no longer available", booking_id),
            )
            return "FAILED"

        conn.execute(
            "UPDATE seats SET status = 'HELD', booking_id = %s, held_until = now() + %s * interval '1 second' "
            "WHERE id = ANY(%s)",
            (booking_id, HOLD_SECONDS, b["seat_ids"]),
        )
        conn.execute(
            "UPDATE bookings SET status = 'HELD', expires_at = now() + %s * interval '1 second' WHERE id = %s",
            (HOLD_SECONDS, booking_id),
        )
        return "HELD"


def mark_failed(booking_id: int, reason: str) -> None:
    with pool.connection() as conn:
        conn.execute(
            "UPDATE bookings SET status = 'FAILED', reason = %s WHERE id = %s AND status = 'QUEUED'",
            (reason, booking_id),
        )
