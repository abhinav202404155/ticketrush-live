import os
import time
import uuid

import httpx

USERS = os.getenv("USERS_URL", "http://localhost:8001")
CATALOG = os.getenv("CATALOG_URL", "http://localhost:8002")
BOOKING = os.getenv("BOOKING_URL", "http://localhost:8003")


def new_user() -> dict:
    """Sign up a fresh random user and return an auth header."""
    email = f"t{uuid.uuid4().hex[:12]}@example.com"
    httpx.post(f"{USERS}/api/users/signup", json={"email": email, "password": "password123"}, timeout=30).raise_for_status()
    r = httpx.post(f"{USERS}/api/users/login", json={"email": email, "password": "password123"}, timeout=30)
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def free_seats(show_id: int = 1) -> list[int]:
    seats = httpx.get(f"{CATALOG}/api/shows/{show_id}/seats", timeout=30).json()
    return [s["id"] for s in seats if s["status"] == "AVAILABLE"]


def wait_until_processed(booking_id: int, headers: dict, timeout: float = 60) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        b = httpx.get(f"{BOOKING}/api/bookings/{booking_id}", headers=headers, timeout=30).json()
        if b["status"] != "QUEUED":
            return b
        time.sleep(0.3)
    raise TimeoutError(f"booking {booking_id} still QUEUED")
