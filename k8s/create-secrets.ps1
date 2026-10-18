# Run from the project root. Builds the Kubernetes Secret + DB seed ConfigMap from your local .env (which is git-ignored).
$ErrorActionPreference = "Stop"
if (-not (Test-Path .env)) { throw ".env not found. Run: copy .env.example .env" }
$e = @{}
Get-Content .env | Where-Object { $_ -match '^\s*[^#\s][^=]*=' } | ForEach-Object { $k, $v = $_ -split '=', 2; $e[$k.Trim()] = $v.Trim() }
kubectl apply -f k8s/00-namespace.yaml
kubectl create secret generic ticketrush-secrets -n ticketrush `
  --from-literal=POSTGRES_USER=$($e.POSTGRES_USER) `
  --from-literal=POSTGRES_PASSWORD=$($e.POSTGRES_PASSWORD) `
  --from-literal=POSTGRES_DB=$($e.POSTGRES_DB) `
  --from-literal=RABBITMQ_DEFAULT_USER=$($e.RABBITMQ_DEFAULT_USER) `
  --from-literal=RABBITMQ_DEFAULT_PASS=$($e.RABBITMQ_DEFAULT_PASS) `
  --from-literal=JWT_SECRET=$($e.JWT_SECRET) `
  --from-literal=ADMIN_KEY=$($e.ADMIN_KEY) `
  --from-literal="DATABASE_URL=postgresql://$($e.POSTGRES_USER):$($e.POSTGRES_PASSWORD)@postgres:5432/$($e.POSTGRES_DB)" `
  --from-literal="RABBITMQ_URL=amqp://$($e.RABBITMQ_DEFAULT_USER):$($e.RABBITMQ_DEFAULT_PASS)@rabbitmq:5672/" `
  --dry-run=client -o yaml | kubectl apply -f -
kubectl create configmap db-init -n ticketrush --from-file=init.sql=db/init.sql --dry-run=client -o yaml | kubectl apply -f -
Write-Host "Secret and db-init created." -ForegroundColor Green
