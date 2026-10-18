# Part 3: Kubernetes (Minikube)

## Files
| File | What it is |
|---|---|
| 00-namespace | our own "folder" inside the cluster |
| 10-config | non-secret settings (hold time, fake work delay, rate limits) |
| 20-postgres | database as a StatefulSet with a 1 GB disk (data survives restarts) |
| 21-rabbitmq | the queue |
| 30-apps | user, catalog, booking, worker, frontend: Deployments + Services + probes + resources |
| 40-autoscaling | HPA (CPU) for the 3 APIs, KEDA (queue length) for the worker |
| 50-ingress | front door to the frontend |
| create-secrets.ps1 | builds the Secret from your git-ignored `.env`, and loads `db/init.sql` |
| build-images.ps1 | builds the 5 images inside Minikube |

## Run (PowerShell, project root)
```powershell
docker compose down                       # free RAM: stop the compose stack first
minikube start --driver=docker --cpus=3 --memory=4096     # 8 GB PC. With 16 GB+ use --cpus=4 --memory=6144
minikube addons enable metrics-server     # lets HPA read CPU
minikube addons enable ingress
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda --namespace keda --create-namespace
kubectl get pods -n keda                  # wait until all Running

powershell -ExecutionPolicy Bypass -File k8s\build-images.ps1
powershell -ExecutionPolicy Bypass -File k8s\create-secrets.ps1
kubectl apply -f k8s/
kubectl get pods -n ticketrush -w         # Ctrl+C when all are Running 1/1
```
Some app pods restart 1-3 times at first while Postgres/RabbitMQ boot. That is normal.

Open the site (keep this terminal open): `kubectl port-forward -n ticketrush svc/frontend 8080:80` then http://localhost:8080
Sign up again: this is a new database.

## Gate: watch autoscaling
Open 3 more terminals and run one each:
```powershell
kubectl get pods -n ticketrush -w
kubectl get hpa -n ticketrush -w
kubectl get scaledobject -n ticketrush -w
```
Then in a 4th terminal fire 100 buyers at one seat (the same test as Part 1, but against the cluster):
```powershell
cd tests
$env:USERS_URL="http://localhost:8080"; $env:CATALOG_URL="http://localhost:8080"; $env:BOOKING_URL="http://localhost:8080"
python -m pytest test_double_booking.py -v
```
Expected: booking-worker pods rise from 1 up to several while the queue is full, and drop back toward 1 about a minute after it empties. user-service may also scale (100 signups use CPU). Test passes = still exactly 1 winner.

## Self-healing demo
```powershell
kubectl delete pod -n ticketrush -l app=catalog-service
kubectl get pods -n ticketrush        # a new catalog pod appears by itself
```

## If it fails
1. `ImagePullBackOff`: images not inside Minikube. Rerun build-images.ps1 (use the same terminal style as above).
2. HPA shows `<unknown>`: metrics-server still starting. Wait 1-2 minutes. Check `minikube addons list`.
3. `no matches for kind "ScaledObject"`: KEDA not installed yet. Install it, then `kubectl apply -f k8s/` again.
4. ScaledObject not READY: run `kubectl describe scaledobject booking-worker -n ticketrush` and send me the output.

## After changing code
Rebuild images, then `kubectl rollout restart deployment -n ticketrush` (same `:dev` tag means pods must be restarted to pick it up).
Reset the database: `kubectl delete statefulset postgres -n ticketrush; kubectl delete pvc data-postgres-0 -n ticketrush; kubectl apply -f k8s/`

## Your turn
Add a 4th HPA for `frontend` (min 1, max 3) by copying one block in 40-autoscaling.yaml. Hint: change only the name.

## Known limits (honest list)
RabbitMQ has no disk: deleting its pod loses queued bookings. Every app gets the whole Secret (simple, not least-privilege).
Control Room "pods" tile and Grafana come in Part 4. Public HTTPS and a real server come in Part 5.
