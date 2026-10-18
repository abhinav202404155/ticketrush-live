# Deploy: Vercel (frontend) + Render (3 APIs + worker) + Neon (database) + CloudAMQP (queue)

What changes compared with Kubernetes: no autoscaling on the live site (free Render = 1 instance each). The worker runs inside the
booking-service container. Autoscaling is shown locally (Minikube + Grafana). Say this honestly in interviews.

## Values you will create (keep them in a private note, never in GitHub)
| Name | Where it comes from |
|---|---|
| NEON_URL | Neon dashboard -> Connect -> **direct** (not "pooled") connection string, ends with ?sslmode=require |
| AMQPS_URL | CloudAMQP instance -> Details -> AMQP URL (starts with amqps://) |
| JWT_SECRET | make one: `[guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")` (SAME value in user-service and booking-service) |
| ADMIN_KEY | another long random value (Control Room password) |

## Render service settings
| | user-service | catalog-service | booking-service |
|---|---|---|---|
| Runtime | Docker | Docker | Docker |
| Root Directory | services/user-service | services/catalog-service | (leave empty) |
| Dockerfile Path | (default) | (default) | deploy/render/booking.Dockerfile |
| Instance type | Free | Free | Free |
| Health Check Path | /healthz | /healthz | /healthz |
| PORT | 8000 | 8000 | 8000 |
| DATABASE_URL | NEON_URL | NEON_URL | NEON_URL |
| DB_POOL_MAX | 3 | 3 | 3 |
| JWT_SECRET | yes | - | yes |
| AUTH_RATE_LIMIT | 30/minute | - | - |
| RABBITMQ_URL | - | - | AMQPS_URL |
| ADMIN_KEY | - | - | yes |
| BOOKING_RATE_LIMIT | - | - | 60/minute |
| HOLD_SECONDS | - | - | 300 |
| WORK_DELAY_MS | - | - | 300 (shows the queue in demos; 0 = full speed) |

## Seed the database (once)
```powershell
docker run --rm -v "${PWD}\db:/db" postgres:16-alpine psql "NEON_URL" -f /db/init_live.sql
```
(`init_live.sql` = 30 days of sessions.) About every 3 weeks run the same command with `topup_sessions.sql` to add the next 30 days; it is safe to repeat.

## Vercel
Import the GitHub repo, **Root Directory = frontend**, framework Vite (auto). Before deploying, put your three Render URLs into
`frontend/vercel.json` (replace USER-SERVICE-URL, CATALOG-SERVICE-URL, BOOKING-SERVICE-URL), commit and push.

## Limits to remember
First visit after idle takes up to ~1 minute (Render wakes) and the site shows a waiting message. 750 shared hours/month. No autoscaling live.
RabbitMQ queue is on CloudAMQP's free shared server. Never share ADMIN_KEY or the connection strings.
