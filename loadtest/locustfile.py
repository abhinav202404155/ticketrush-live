"""Rush simulation: many buyers sign up, then keep booking seats. Most go for 10 'hot' shows so seats really collide.
Run (see docs/PART4.md). Results go to CSV files. Nothing here is invented: all numbers come from the run."""
import random
import time
import uuid

from locust import HttpUser, between, events, task
from locust.exception import StopUser

HOT_SHOWS = list(range(4, 14))      # sessions 4..13: everybody wants these -> contention
ALL_SHOWS = list(range(4, 400))


class Buyer(HttpUser):
    wait_time = between(2, 5)

    def on_start(self):
        creds = {"email": f"load{uuid.uuid4().hex[:12]}@example.com", "password": "password123"}
        self.client.post("/api/users/signup", json=creds, name="signup")
        r = self.client.post("/api/users/login", json=creds, name="login")
        if not r.ok:
            raise StopUser()
        self.headers = {"Authorization": "Bearer " + r.json()["access_token"]}

    @task
    def book(self):
        show = random.choice(HOT_SHOWS if random.random() < 0.8 else ALL_SHOWS)
        seats = self.client.get(f"/api/shows/{show}/seats", name="/api/shows/[id]/seats").json()
        free = [s["id"] for s in seats if s["status"] == "AVAILABLE"]
        if not free:
            return
        pick = random.sample(free, k=min(len(free), random.randint(1, 3)))
        t0 = time.time()
        with self.client.post("/api/bookings", json={"show_id": show, "seat_ids": pick}, headers=self.headers,
                              name="/api/bookings", catch_response=True) as r:
            if r.status_code != 202:
                r.failure(f"HTTP {r.status_code}")
                return
            booking_id = r.json()["booking_id"]
        status = "QUEUED"
        for _ in range(120):                      # wait in the queue up to ~60 s
            time.sleep(0.5)
            status = self.client.get(f"/api/bookings/{booking_id}", headers=self.headers,
                                     name="/api/bookings/[id]").json()["status"]
            if status != "QUEUED":
                break
        # Custom row in the report: time from clicking "reserve" until the worker decided (HELD or FAILED)
        events.request.fire(request_type="QUEUE", name=f"reserve -> {status}", response_time=(time.time() - t0) * 1000,
                            response_length=0, exception=None)
        if status == "HELD":
            self.client.post(f"/api/bookings/{booking_id}/pay", json={"card_number": "4242424242424242"},
                             headers=self.headers, name="/api/bookings/[id]/pay")
