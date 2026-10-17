"""Happy path + mock payment decline. Needs the docker-compose stack running."""
import httpx
from helpers import BOOKING, free_seats, new_user, wait_until_processed


def test_book_hold_and_pay():
    h = new_user()
    seat = free_seats()[0]
    r = httpx.post(f"{BOOKING}/api/bookings", json={"show_id": 1, "seat_ids": [seat]}, headers=h, timeout=30)
    assert r.status_code == 202 and r.json()["status"] == "QUEUED"
    b = wait_until_processed(r.json()["booking_id"], h)
    assert b["status"] == "HELD"
    paid = httpx.post(f"{BOOKING}/api/bookings/{b['booking_id']}/pay", json={"card_number": "4242424242424242"}, headers=h, timeout=30)
    assert paid.json()["status"] == "CONFIRMED"


def test_declined_card_keeps_hold():
    h = new_user()
    seat = free_seats()[0]
    bid = httpx.post(f"{BOOKING}/api/bookings", json={"show_id": 1, "seat_ids": [seat]}, headers=h, timeout=30).json()["booking_id"]
    wait_until_processed(bid, h)
    r = httpx.post(f"{BOOKING}/api/bookings/{bid}/pay", json={"card_number": "4000000000000000"}, headers=h, timeout=30)
    assert r.status_code == 402


def test_flash_show_not_open_yet():
    h = new_user()
    r = httpx.post(f"{BOOKING}/api/bookings", json={"show_id": 3, "seat_ids": [101]}, headers=h, timeout=30)
    assert r.status_code == 403
