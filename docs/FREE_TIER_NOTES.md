# Free-tier notes (checked 2026-10-18 by web search; limits change, re-check before relying on them)

## Oracle Cloud "Always Free" (Plan A: real server)
- Needs a **credit/debit card for identity verification**. One source says a real physical card in your own name is required and virtual/prepaid/single-use cards are refused. **Flagged: needs your decision.**
- Ampere A1 (ARM) allowance: older articles say 4 OCPU / 24 GB. Two newer sources (dated Sept-Oct 2026) say Oracle **halved it to 2 OCPU / 12 GB on 2026-06-15**. Plan for 2 OCPU / 12 GB and read the number in your own console.
- Also reported: capacity in a region is not guaranteed (can wait days), idle instances can be reclaimed, home region cannot be changed later, 200 GB total block storage, 10 TB/month egress.
- Our whole stack needs roughly 3 GB of RAM, so 2 OCPU / 12 GB is enough. Images must be arm64 (our CI builds both).
- Staying inside Always Free limits costs nothing; going over, or upgrading to Pay As You Go, can.

## Cloudflare Tunnel (Plan B: site runs on your PC)
- **Quick tunnel** (`cloudflared tunnel --url ...`): no account, no card, random `*.trycloudflare.com` HTTPS URL, lives until you press Ctrl+C. Cloudflare says it is for testing, **no uptime guarantee**, and returns HTTP 429 above a concurrent-request limit.
- **Named tunnel** (fixed hostname): free account, but needs a **domain on Cloudflare DNS** (a domain normally costs money, so not Rs 0).

## GitHub Actions and GitHub Container Registry (CI/CD)
- GitHub docs: Actions on standard runners is free for **public** repositories. Free accounts also list 500 MB Packages storage / 2,000 min for private repos. Keep the repo **public**.
- Sources describe GHCR as free for public packages. Re-check the Packages billing page if you ever make the repo private.

## Not re-verified today
- DuckDNS (free subdomain) and Let's Encrypt (free HTTPS certificates). Both are normally free; confirm on their sites before Plan A.

## Cost guardrails
- Keep the repo public. Never enter a card anywhere except Oracle verification (if you choose Plan A).
- Oracle: create only Always Free shapes (look for the "Always Free-eligible" label), do not upgrade the account, set a budget alert at Rs 1 if the console offers one.
- Do not expose Grafana, Prometheus or RabbitMQ to the internet. Only the frontend is public.

---
# Plan C: Render + Vercel + Neon + CloudAMQP (checked 2026-10-18 by web search)

## Render (backend: 3 web services)
- Hobby workspace is $0. Free web service: 512 MB RAM, 0.1 CPU, **sleeps after 15 min without traffic, ~1 minute to wake**, **single instance (no autoscaling)**, no persistent disk. All free services in a workspace **share 750 instance hours per month**; when used up they are **suspended until next month** (extra bandwidth is billed only if a card is on file).
- Several sources say **no credit card is needed** for the free tier. If Render ever asks for a card, stop and decide first.
- **Free Postgres expires 30 days after creation** (+14 days grace, then deleted). We do NOT use it.
- **Background workers and private services have no free tier** (they start at Starter, paid). This is why the worker runs inside the booking-service container.
- 3 services x 24h x 30 days would exceed 750 hours if they never slept. Do not set up uptime pings on Render.

## Vercel (frontend)
- Hobby plan: free, no time limit, no card. **Personal, non-commercial use only** (fine for a portfolio demo, not for charging money). ~100 GB bandwidth/month; if a limit is exceeded, that feature pauses (no bill, Hobby cannot buy extra usage).

## Neon (Postgres)
- Free plan: no card, no expiry, 0.5 GB storage, 100 CU-hours/month per project, compute **scales to zero after 5 minutes idle** (first query after that is a bit slower). Our database is a few tens of MB.

## CloudAMQP (RabbitMQ)
- "Little Lemur" free plan: 1M messages/month, 20 concurrent connections, 100 queues, max 10,000 queued messages, shared server. Over the message limit the instance is blocked (not billed). **Card requirement was not stated in the sources I found: check at sign-up and stop if it asks for one.**
