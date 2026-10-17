"""THE key test: 100 different users fight for ONE seat at the same instant.
Exactly one must win. Run the stack with `--scale booking-worker=3` for a harder test."""
from concurrent.futures import ThreadPoolExecutor

import httpx
from helpers import BOOKING, CATALOG, free_seats, new_user, wait_until_processed

N = 100


def test_one_seat_100_buyers_one_winner():
    seat = free_seats()[-1]
    with ThreadPoolExecutor(max_workers=20) as ex:
        users = list(ex.map(lambda _: new_user(), range(N)))

    def attempt(h):
        r = httpx.post(f"{BOOKING}/api/bookings", json={"show_id": 1, "seat_ids": [seat]}, headers=h, timeout=60)
        assert r.status_code == 202, r.text
        return wait_until_processed(r.json()["booking_id"], h)

    with ThreadPoolExecutor(max_workers=N) as ex:   # all 100 fire together
        results = list(ex.map(attempt, users))

    winners = [r for r in results if r["status"] == "HELD"]
    losers = [r for r in results if r["status"] == "FAILED"]
    assert len(winners) == 1, f"expected 1 winner, got {len(winners)}"
    assert len(losers) == N - 1
    seats = httpx.get(f"{CATALOG}/api/shows/1/seats", timeout=30).json()
    assert next(s for s in seats if s["id"] == seat)["status"] == "HELD"
