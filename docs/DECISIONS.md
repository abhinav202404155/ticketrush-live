# Decisions
- FastAPI: automatic /docs pages make learning and demos easy.
- One shared Postgres for all services: simplest for a demo. Trade-off: services are coupled via the schema.
- Queue position = count of QUEUED rows with smaller id. Simple and exact; no RabbitMQ internals needed.
- Seat safety = SELECT ... FOR UPDATE in id order inside one transaction (no double-sell, no deadlock).
- Expiry is lazy (hold time checked in SQL), so no background cleanup process.
- Rate limits via slowapi, set high in local .env so tests can run; set low in production.
