# Load test report (fill in ONLY with numbers from your own run)

Date: ____   Machine: ____ RAM, Minikube cpus/memory: ____
Command: `locust ... --users __ --spawn-rate __ --run-time __`

| Measure | Value | Where to read it |
|---|---|---|
| Peak queue length | | Grafana "Queue length" |
| Workers: start -> peak -> end | | Grafana "Worker pods" / Control Room log |
| API pods peak (user / catalog / booking) | | Grafana "API pods" |
| Bookings attempted (POST /api/bookings) | | `loadtest/results_stats.csv` |
| Seats won (reserve -> HELD) | | row "reserve -> HELD" |
| Seats lost (reserve -> FAILED) | | row "reserve -> FAILED" |
| Median / 95th percentile wait in queue | | rows "reserve -> ..." |
| HTTP errors (failures) | | results_failures.csv |
| Time to drain queue after load stopped | | Grafana |
| double_booked_seats | | integrity.sql (must be 0) |
| seats_sold == sold_seats_in_confirmed_bookings | | integrity.sql |

Notes / what limited the test (RAM, Pending pods, port-forward):
