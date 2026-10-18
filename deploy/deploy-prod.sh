#!/usr/bin/env bash
# Run ON THE SERVER (k3s) inside the cloned repo, after creating .env there.
# Usage: OWNER=<your-github-username-lowercase> ./deploy/deploy-prod.sh
set -euo pipefail
: "${OWNER:?set OWNER=<your github username in lowercase>}"
set -a; source .env; set +a
kubectl apply -f k8s/00-namespace.yaml
kubectl create secret generic ticketrush-secrets -n ticketrush \
  --from-literal=POSTGRES_USER="$POSTGRES_USER" --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  --from-literal=POSTGRES_DB="$POSTGRES_DB" --from-literal=RABBITMQ_DEFAULT_USER="$RABBITMQ_DEFAULT_USER" \
  --from-literal=RABBITMQ_DEFAULT_PASS="$RABBITMQ_DEFAULT_PASS" --from-literal=JWT_SECRET="$JWT_SECRET" \
  --from-literal=ADMIN_KEY="$ADMIN_KEY" \
  --from-literal=DATABASE_URL="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@postgres:5432/$POSTGRES_DB" \
  --from-literal=RABBITMQ_URL="amqp://$RABBITMQ_DEFAULT_USER:$RABBITMQ_DEFAULT_PASS@rabbitmq:5672/" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl create configmap db-init -n ticketrush --from-file=init.sql=db/init.sql --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f deploy/prod-config.yaml
for f in k8s/20-postgres.yaml k8s/21-rabbitmq.yaml k8s/40-autoscaling.yaml k8s/50-ingress.yaml k8s/60-monitoring.yaml; do kubectl apply -f "$f"; done
# Use the images built by GitHub Actions instead of the local ":dev" ones
sed -E -e "s#image: ticketrush/([a-z-]+):dev#image: ghcr.io/${OWNER}/ticketrush-\1:latest#" \
       -e "s#imagePullPolicy: IfNotPresent.*#imagePullPolicy: Always#" k8s/30-apps.yaml | kubectl apply -f -
echo "Applied. Watch: kubectl get pods -n ticketrush -w"
