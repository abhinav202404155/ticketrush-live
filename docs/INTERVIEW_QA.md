# 20 viva / interview questions about TicketRush (answers match this exact project)

1. **What problem does it solve?** Ticket sites crash or double-sell when thousands click at once. TicketRush puts requests in a queue and lets workers lock seats one booking at a time.
2. **How do you stop the same seat being sold twice?** A worker runs one DB transaction: `SELECT ... FOR UPDATE` on the seat rows, checks they are free, then marks them HELD. A second worker wanting the same seat waits for the first commit and then sees it taken. The 100-buyers-one-seat test proves it.
3. **Why lock rows in id order?** If two bookings lock seats in different orders they can wait on each other forever (deadlock). One fixed order removes that.
4. **Why a queue instead of booking directly in the API?** The API answers fast with 202 Accepted and absorbs bursts. Workers do the slow, safe part at a pace the database can handle, and we can add workers.
5. **What if a worker crashes mid-booking?** The message is acknowledged only after the work finishes, so RabbitMQ redelivers it. The DB transaction is all-or-nothing, and a booking that is no longer QUEUED is skipped, so duplicates are harmless.
6. **How does the 5-minute hold work?** The worker sets HELD with a `held_until` time. Expiry is checked inside SQL (a HELD seat past its time counts as free), so no cleanup job is needed.
7. **How is the queue position calculated?** Count of bookings still QUEUED with an id less than or equal to mine (ids grow in arrival order).
8. **Why HPA for APIs but KEDA for the worker?** API load shows up as CPU, so HPA on CPU fits. A queue worker can be idle on CPU while 1000 messages wait, so KEDA scales on queue length.
9. **How does HPA decide?** It compares average CPU to the pod's CPU request (that is why requests are set) and adds pods above the 60% target.
10. **Readiness vs liveness probe?** Readiness: should this pod receive traffic yet. Liveness: is it stuck, restart it (self-healing).
11. **Why a StatefulSet for Postgres?** It keeps a persistent disk (PVC) that survives pod restarts, unlike a Deployment's disposable pods.
12. **How are secrets handled?** Passwords live in a git-ignored `.env`, turned into a Kubernetes Secret by a script. Honest limit: Secrets are only base64, and every pod receives the whole Secret.
13. **How does login work?** Passwords are hashed with bcrypt; login returns a signed JWT; other services verify it with the shared secret. Wrong email and wrong password give the same error message so attackers learn nothing.
14. **How is rate limiting done and what are its limits?** slowapi per client IP. Limits are counted per pod in memory, and the client IP comes from X-Forwarded-For, which a client can fake. Fine for a demo, not for serious abuse protection.
15. **What happens if the RabbitMQ pod dies?** It has no disk, so waiting bookings are lost and their rows stay QUEUED. Fix: a persistent volume plus a recovery job that re-publishes old QUEUED rows.
16. **How did you test concurrency?** A pytest that fires 100 users at one seat (exactly 1 must win), a Locust rush with many users, and an SQL check that no seat appears in two confirmed bookings.
17. **Why mock payments?** Real payments need a gateway, business registration and compliance, and the project is Rs 0. The flow is the same, only the final charge is simulated.
18. **How does Prometheus find the pods?** Kubernetes service discovery plus pod annotations (`prometheus.io/scrape`). New pods created by autoscaling are found automatically.
19. **Why multi-architecture images?** My PC is amd64 but free ARM servers (Oracle) are arm64. CI builds both so one tag runs on either.
20. **What would you improve?** Separate database per service, queue on a persistent volume with recovery, Redis-based shared rate limiting, real observability alerts, load-test with a proper environment, and real payments through a gateway.
