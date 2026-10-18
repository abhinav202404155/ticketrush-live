# Resume bullets, LinkedIn post, interview scripts

RULE: replace every [X] with a number from YOUR own test (docs/LOAD_TEST_REPORT.md). If you did not measure it, delete the sentence.

## Resume bullets (pick 3-4)
- Built **TicketRush**, a flash-sale ticket booking platform (FastAPI, React, PostgreSQL, RabbitMQ) deployed on Kubernetes; requests go through a waiting-room queue so traffic bursts never overload the database.
- Prevented double-booking with row-level locking (`SELECT FOR UPDATE`, fixed lock order); verified with a [100]-user concurrent test and a Locust rush of [X] users: [0] double-booked seats.
- Autoscaled the system: HPA on CPU for APIs and KEDA on RabbitMQ queue length for workers; under load workers scaled from [1] to [X] pods and back down after the queue drained.
- Added Prometheus + Grafana monitoring and a live Control Room page; built a GitHub Actions pipeline that publishes multi-arch (amd64/arm64) images to GHCR; total hosting cost Rs 0.

## LinkedIn post (draft)
I built TicketRush to learn how ticket sites survive the "everyone clicks at the same second" problem. Bookings go into a RabbitMQ queue, workers lock seats safely in PostgreSQL, and Kubernetes (HPA + KEDA) adds workers when the queue grows. In my load test, [X] users competed for seats: [X] pods at peak, [0] double-booked seats. Stack: FastAPI, React, PostgreSQL, RabbitMQ, Kubernetes, Prometheus/Grafana, GitHub Actions. Demo project, mock payments only. Code: [repo link]. #kubernetes #devops #python #learning

## 2-minute script
"TicketRush is a ticket-booking site built to survive flash sales. When thousands click Book at once, normal sites crash or sell a seat twice. Here the API only accepts the request and puts it on a RabbitMQ queue, so the user sees 'You are number N'. Workers take bookings one by one; each runs a database transaction that locks the seat rows, so a seat can only go to one person. Seats are held five minutes, then a mock payment confirms them. On Kubernetes the APIs scale on CPU and the workers scale on queue length with KEDA. I tested it with [X] simulated users, saw workers go from [1] to [X] and back, and checked that zero seats were double-sold. Everything runs on free tools."

## 5-minute script (add these parts after the 2-minute one)
1. Show the website: search, pick a show, seat map, queue screen, payment, My bookings.
2. Show Grafana during a rush: queue length rising, worker pods rising, then falling.
3. Explain the lock: two workers want seat A1, the second waits, then sees it taken.
4. Explain one failure you handled (worker crash gives redelivery; expired hold counts as free).
5. Honest limits: queue has no disk, shared database, mock payments, demo-grade rate limiting. Say what you would fix first.
