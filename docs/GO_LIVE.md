# Go live at Rs 0

Choose ONE plan. Plan B needs no card and works today. Plan A is a real always-on server but needs a card.

## Step 0 (both plans): put the code on GitHub (public repo)
1. On github.com create a **public** repo named `ticketrush` (no README).
2. In the project folder (PowerShell):
```powershell
git status                      # .env must NOT be listed (it is git-ignored)
git add .
git commit -m "TicketRush: parts 1-5"
git branch -M main
git remote add origin https://github.com/<your-username>/ticketrush.git
git push -u origin main
```
3. Open the repo -> **Actions** tab. The `ci` workflow runs (about 10-20 min first time, it builds 5 images for amd64 and arm64).
4. When green: your profile -> Packages -> open each `ticketrush-*` package -> Package settings -> change visibility to **Public** (needed only for Plan A).

## Plan B: live from your PC (no card, URL changes each time)
Before sharing a link, make the site safe:
1. Edit `.env`: set `JWT_SECRET` and `ADMIN_KEY` to long random values. Make one with:
```powershell
[guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
```
Do NOT change `POSTGRES_PASSWORD` or the RabbitMQ password (the database already uses the old one).
2. Load the secrets again and switch to public-site settings (low rate limits):
```powershell
powershell -ExecutionPolicy Bypass -File k8s\create-secrets.ps1
kubectl apply -f deploy/prod-config.yaml
```
3. Rebuild the changed images (proxy headers) and restart everything:
```powershell
powershell -ExecutionPolicy Bypass -File k8s\rebuild-images.ps1 -Services user-service,catalog-service,booking-service,frontend
kubectl rollout restart deployment/booking-worker deployment/prometheus deployment/grafana -n ticketrush
kubectl get pods -n ticketrush        # wait for all 1/1
```
4. Install the tunnel tool, then close and reopen PowerShell:
```powershell
winget install Cloudflare.cloudflared
```
5. Terminal 1: `kubectl port-forward -n ticketrush svc/frontend 18080:80`
   Terminal 2: `cloudflared tunnel --url http://localhost:18080`
   It prints `https://something.trycloudflare.com`. That is your public URL.
6. **Gate:** turn Wi-Fi off on your phone, use mobile data, open the URL, sign up and book a seat.
7. Limits to remember: works only while your PC, Minikube and both terminals are running; the URL changes every run; Cloudflare gives no uptime promise; keep Windows from sleeping. Stop with Ctrl+C.
Do NOT tunnel Grafana or Prometheus.

## Plan A: always-on server on Oracle Cloud (needs a real card for verification)
Overview (I will give the exact HTTPS and DuckDNS files once you confirm you want this plan):
1. Create an Oracle Cloud account, choose the home region carefully, create an **Always Free** Ampere A1 VM (Ubuntu 24.04 aarch64, 2 OCPU / 12 GB). Open ports 80 and 443 in the VCN security list and on the VM firewall.
2. On the VM: install k3s (`curl -sfL https://get.k3s.io | sh -`), git, helm; install KEDA with helm (same commands as Part 3).
3. `git clone` your repo, create `.env` (strong secrets), run `OWNER=<github-username-lowercase> ./deploy/deploy-prod.sh`.
4. Free name: DuckDNS subdomain -> VM public IP. Free HTTPS: Let's Encrypt through k3s's built-in Traefik.
5. Add the `SITE_URL` repo variable so `uptime.yml` checks the site every 30 minutes.
