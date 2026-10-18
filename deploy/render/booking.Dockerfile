# Render's free plan has no background worker, so ONE container runs both jobs:
#   1) the booking API (web)   2) the queue worker (a loop that restarts it if it crashes)
# Build context = repository root (Render: leave "Root Directory" empty).
FROM python:3.12-slim
WORKDIR /srv
COPY services/booking-service/requirements.txt api-requirements.txt
COPY worker/requirements.txt worker-requirements.txt
RUN pip install --no-cache-dir -r api-requirements.txt -r worker-requirements.txt
COPY services/booking-service/app ./app
COPY worker ./worker
RUN useradd -m appuser
USER appuser
ENV METRICS_PORT=9100
CMD ["sh", "-c", "(while true; do python -m worker.main; echo worker stopped, restarting; sleep 3; done) & exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips '*'"]
