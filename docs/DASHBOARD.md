# Control Room dashboard (autoscaling + microservices)

Open `/#/control` on the site and enter `ADMIN_KEY`. One backend call (`GET /api/admin/overview`) feeds the whole page.

## What it shows
| Section | Source |
|---|---|
| Health + latency of user / catalog / booking services, RabbitMQ, Postgres, workers | `/healthz` probes, RabbitMQ passive queue declare, `SELECT 1` |
| Queue depth, workers, success rate, seats sold, booking status | RabbitMQ + PostgreSQL (works everywhere) |
| Replicas over time, CPU vs HPA target, req/s, p95, processed/s, **scaling events** | Prometheus (only on Kubernetes) |

The page detects its environment. **Kubernetes + Prometheus** = full autoscaling charts. **Render free tier** = badge says "Single instance" and the autoscaling charts say what is missing. It never shows invented numbers.

## Settings (all optional)
| Env var | Default | Meaning |
|---|---|---|
| `PROMETHEUS_URL` | empty | Set in `k8s/10-config.yaml` already |
| `USER_SERVICE_URL`, `CATALOG_SERVICE_URL` | `http://user-service:8000`, `http://catalog-service:8000` | Where to probe `/healthz` (Render: the public onrender URLs) |
| `HPA_CPU_TARGET_PERCENT` | `60` | Must equal the HPA target in `k8s/40-autoscaling.yaml` |
| `DASHBOARD_PUBLIC` | `false` | `true` = no key needed. Page shows only aggregates (no emails, no booking details) |
| `OVERVIEW_CACHE_SECONDS` | `3` | 20 open dashboards still cost one set of queries per 3 s |

## Step by step

### 1. Copy the files in (PowerShell)
```powershell
# extract ticketrush-dashboard-patch.zip, then copy its contents over your project folder (Replace)
cd C:\Users\LENOVO\Downloads\ticketrush-part1\ticketrush
pip install pytest httpx -r services\booking-service\requirements.txt
python -m pytest tests\test_dashboard_overview.py -v     # expect: 8 passed
cd frontend; npm install; npm run build; cd ..           # expect: built in ...
```

### 2. Local check with Docker Compose
```powershell
docker compose down -v
docker compose up --build --scale booking-worker=3
```
Open http://localhost:3000/#/control. Expect badge "Single instance", **Workers = 3**, all services green, autoscaling charts empty with a note.

### 3. Kubernetes (this is where autoscaling shows)
```powershell
powershell -ExecutionPolicy Bypass -File k8s\rebuild-images.ps1 -Services booking-service,frontend
kubectl rollout restart deployment/booking-service deployment/frontend -n ticketrush
kubectl get pods -n ticketrush                    # wait for all 1/1
kubectl port-forward -n ticketrush svc/frontend 18080:80
```
Open http://localhost:18080/#/control. Expect badge "Kubernetes · autoscaling on". If it still says "Single instance", check `PROMETHEUS_URL` and that the Prometheus pod is 1/1.

Start a rush in a second terminal (change `--users` to what your PC can take):
```powershell
pip install locust
cd loadtest
locust -f locustfile.py --host http://localhost:18080 --headless --users 200 --spawn-rate 10 --run-time 3m --csv results
```
Watch: queue depth rises, KEDA adds workers, CPU line crosses the red HPA target, API replicas step up, scaling events list fills. After the test stops, replicas fall back (about a minute).
Then run `loadtest\integrity.sql` and copy only real numbers into `docs/LOAD_TEST_REPORT.md`.

### 4. Live site (Vercel + Render)
Render -> booking-service -> Environment, add:
`USER_SERVICE_URL` = your user-service onrender URL, `CATALOG_SERVICE_URL` = your catalog-service onrender URL. Save (it redeploys).
Notes: opening the dashboard pings the other two free services, so it **wakes them** and uses free instance hours. Live shows "Single instance" because free Render has no autoscaler. Prove autoscaling with a screenshot or screen recording from step 3 in the README.

### 5. Publish
```powershell
git add .
git commit -m "Control Room dashboard: service health, autoscaling charts, scaling events"
git push
```

## Troubleshooting
| Symptom | Cause / fix |
|---|---|
| "That key was not accepted" | Key must equal `ADMIN_KEY` of booking-service (Render env or `.env`) |
| user/catalog show Unreachable on Render | `*_SERVICE_URL` not set, or service asleep (wait ~1 min) |
| Workers shows 0, red | No worker connected to the queue |
| Charts empty on Kubernetes | Prometheus not ready; `kubectl get pods -n ticketrush`; check Targets at the Prometheus port-forward |
| CPU chart flat near 0 | Load too small to cross the target; raise `--users` |

## Limits (honest)
Scaling history = Prometheus retention (2 days, no disk: lost if its pod restarts). "Desired replicas" are not shown (needs the Kubernetes API); the page shows replicas that are actually running. CPU is process CPU divided by the pod's CPU request, which is what the HPA compares with its target.
