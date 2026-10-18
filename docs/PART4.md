# Part 4: monitoring + rush load test (see chat for step-by-step)
- k8s/60-monitoring.yaml: Prometheus + Grafana (dashboard "TicketRush: rush dashboard" is loaded automatically)
- k8s/10-config.yaml: adds PROMETHEUS_URL and very high rate limits for load tests (lower them on a public site)
- loadtest/locustfile.py + integrity.sql: the rush and the double-booking check
- Control Room now shows worker/API pod counts and a log of scaling events (needs Prometheus; shows n/a under docker-compose)
Limits: Prometheus and Grafana keep no disk (history lost on restart). Control Room event log exists only while the page is open.
