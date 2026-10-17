# TicketRush (demo project, mock payments only, do not use real passwords)

Flash-sale ticket booking: waiting-room queue, atomic seat locking, autoscaling workers.

## Build parts
| Part | Contents | Status |
|---|---|---|
| 1 | Postgres, RabbitMQ, user/catalog/booking APIs, worker, tests (docker-compose) | this zip |
| 2 | React frontend + Control Room page | next |
| 3 | Kubernetes: manifests, Ingress, Secrets, HPA, KEDA | |
| 4 | Prometheus, Grafana, Locust "rush" load test | |
| 5 | CI/CD, free hosting, go-live guide, README polish, interview pack | |

## Run Part 1 (Windows PowerShell, Docker Desktop running)
```powershell
copy .env.example .env
docker compose up --build --scale booking-worker=3
```
First start takes a few minutes. Wait for "worker ready" lines.

| URL | What |
|---|---|
| http://localhost:8001/docs | user-service (signup, login) |
| http://localhost:8002/docs | catalog-service (shows, seats) |
| http://localhost:8003/docs | booking-service (book, pay, admin stats) |
| http://localhost:15672 | RabbitMQ UI (login from your .env) |

## Run the tests (second terminal)
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r tests\requirements.txt
cd tests
python -m pytest -v
```
`test_double_booking.py` = 100 users, 1 seat, exactly 1 winner. It takes about a minute (100 bcrypt signups).

## Try it by hand
In http://localhost:8001/docs call `POST /api/users/signup`, then `/login`, copy the token, click **Authorize** in
http://localhost:8003/docs, then `POST /api/bookings` with `{"show_id":1,"seat_ids":[1,2]}`, `GET /api/bookings/{id}`,
`POST /api/bookings/{id}/pay` with `{"card_number":"4242424242424242"}`. Card ending `0000` is declined.

## Flash release demo
Show 3 opens 1 hour after first start. To open it in 1 minute instead:
```powershell
docker compose exec postgres psql -U ticketrush -c "UPDATE shows SET opens_at = now() + interval '1 minute' WHERE id = 3;"
```
Reset everything: `docker compose down -v` (deletes the database volume).

## How a booking flows
`POST /api/bookings` -> row saved as QUEUED -> message to RabbitMQ -> a worker locks the seat rows
(`SELECT ... FOR UPDATE`, in id order) -> HELD for 5 min -> `/pay` -> CONFIRMED. Seat taken meanwhile -> FAILED.
Expired holds are treated as free again, so no cleanup job is needed.

## Learn-by-doing ("Your turn" for Part 1)
Add a `GET /api/shows/{id}/stats` endpoint in catalog-service that returns counts of AVAILABLE / HELD / SOLD seats.
Hint: `SELECT status, COUNT(*) ... GROUP BY status` (copy the pattern from `list_shows`).
