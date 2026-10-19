"""Read-only observability layer behind the Control Room dashboard.

One call, `build_overview()`, gathers everything the dashboard needs:

  * service health + latency         (HTTP probes of each microservice)
  * broker status                    (RabbitMQ passive queue declare: depth + consumers)
  * database status + booking stats  (PostgreSQL)
  * time series for autoscaling      (Prometheus range queries, if PROMETHEUS_URL is set)
  * scaling events                   (derived from the pod-count series)

The module works in two environments and says honestly which one it is in:
  - "kubernetes":      Prometheus reachable -> pod counts, CPU vs HPA target, scaling events.
  - "single-instance": no Prometheus (e.g. Render free tier) -> health, queue, DB stats only.

Only a fixed set of PromQL queries is ever sent (no user-supplied PromQL).
"""
from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pika

log = logging.getLogger("observability")

APPS = ("user-service", "catalog-service", "booking-service")
WORKER = "booking-worker"
QUEUE = "booking_requests"


@dataclass(frozen=True)
class Settings:
    prometheus_url: str = field(default_factory=lambda: os.getenv("PROMETHEUS_URL", "").rstrip("/"))
    user_url: str = field(default_factory=lambda: os.getenv("USER_SERVICE_URL", "http://user-service:8000").rstrip("/"))
    catalog_url: str = field(default_factory=lambda: os.getenv("CATALOG_SERVICE_URL", "http://catalog-service:8000").rstrip("/"))
    probe_timeout: float = float(os.getenv("PROBE_TIMEOUT_SECONDS", "2.5"))
    prom_timeout: float = float(os.getenv("PROM_TIMEOUT_SECONDS", "3"))
    cache_ttl: float = float(os.getenv("OVERVIEW_CACHE_SECONDS", "3"))
    hpa_cpu_target: float = float(os.getenv("HPA_CPU_TARGET_PERCENT", "60"))  # must match k8s/40-autoscaling.yaml
    # CPU *requests* per app (k8s/30-apps.yaml). HPA utilisation = usage / request.
    cpu_request: dict = field(default_factory=lambda: {
        "user-service": 0.1, "catalog-service": 0.1, "booking-service": 0.1, WORKER: 0.05})


# --------------------------------------------------------------------------- helpers
def _num(v) -> float | None:
    """Prometheus sends 'NaN' / '+Inf' as strings. JSON cannot carry them, so they become None."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _http_json(url: str, timeout: float):
    with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 (URL comes from our own env config)
        return json.load(r)


class Prometheus:
    """Tiny Prometheus HTTP API client. Every failure becomes None, never an exception."""

    def __init__(self, base_url: str, timeout: float):
        self.base, self.timeout = base_url, timeout

    @property
    def enabled(self) -> bool:
        return bool(self.base)

    def range(self, promql: str, start: float, end: float, step: int) -> list[dict] | None:
        qs = urllib.parse.urlencode({"query": promql, "start": start, "end": end, "step": step})
        try:
            data = _http_json(f"{self.base}/api/v1/query_range?{qs}", self.timeout)
            return data["data"]["result"] if data.get("status") == "success" else None
        except Exception as exc:  # network, timeout, bad JSON: the dashboard must keep working
            log.warning("prometheus query failed: %s", exc)
            return None


def _series(result: list[dict] | None, label: str | None = None) -> dict[str, list[list]]:
    """[{metric, values}] -> {label_value: [[unix_ts, value|None], ...]} (label None -> single series 'all')."""
    out: dict[str, list[list]] = {}
    for item in result or []:
        key = item["metric"].get(label, "all") if label else "all"
        out[key] = [[int(ts), _num(v)] for ts, v in item["values"]]
    return out


def scaling_events(pods: dict[str, list[list]], limit: int = 20) -> list[dict]:
    """Turn 'pod count over time' into 'what scaled, when, from -> to' (newest first)."""
    events = []
    for app, points in pods.items():
        prev = None
        for ts, val in points:
            if val is None:
                continue
            if prev is not None and val != prev:
                events.append({"ts": ts, "app": app, "from": int(prev), "to": int(val),
                               "direction": "up" if val > prev else "down"})
            prev = val
    return sorted(events, key=lambda e: e["ts"], reverse=True)[:limit]


def _last(points: list[list] | None):
    for _, v in reversed(points or []):
        if v is not None:
            return v
    return None


# --------------------------------------------------------------------------- probes
def probe_http(name: str, base_url: str, timeout: float) -> dict:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(f"{base_url}/healthz", timeout=timeout) as r:  # noqa: S310
            ok = r.status == 200
        return {"name": name, "status": "up" if ok else "down", "latency_ms": round((time.perf_counter() - started) * 1000)}
    except Exception as exc:
        return {"name": name, "status": "down", "latency_ms": None, "detail": type(exc).__name__}


def probe_broker(url: str) -> dict:
    """Passive declare asks RabbitMQ for the queue's depth and consumer count without changing anything."""
    started = time.perf_counter()
    try:
        params = pika.URLParameters(url)
        params.socket_timeout, params.stack_timeout, params.connection_attempts = 2.5, 4.0, 1
        connection = pika.BlockingConnection(params)
        try:
            q = connection.channel().queue_declare(queue=QUEUE, passive=True)
            return {"name": "rabbitmq", "status": "up", "queue_depth": q.method.message_count,
                    "consumers": q.method.consumer_count, "latency_ms": round((time.perf_counter() - started) * 1000)}
        finally:
            connection.close()
    except Exception as exc:
        return {"name": "rabbitmq", "status": "down", "queue_depth": None, "consumers": None,
                "latency_ms": None, "detail": type(exc).__name__}


def database_overview(pool, window_minutes: int) -> dict:
    started = time.perf_counter()
    with pool.connection() as conn:
        conn.execute("SELECT 1")
        latency = round((time.perf_counter() - started) * 1000)
        counts = {r["status"]: r["n"] for r in conn.execute(
            "SELECT status, COUNT(*) AS n FROM bookings GROUP BY status").fetchall()}
        seats = {r["status"]: r["n"] for r in conn.execute(
            "SELECT status, COUNT(*) AS n FROM seats GROUP BY status").fetchall()}
        # One row per minute (even empty minutes), so the chart has no gaps.
        rows = conn.execute(
            """
            SELECT m.minute AS ts,
                   COUNT(b.id)                                   AS requests,
                   COUNT(b.id) FILTER (WHERE b.status = 'CONFIRMED') AS confirmed,
                   COUNT(b.id) FILTER (WHERE b.status = 'FAILED')    AS failed
            FROM generate_series(date_trunc('minute', now()) - make_interval(mins => %s),
                                 date_trunc('minute', now()), interval '1 minute') AS m(minute)
            LEFT JOIN bookings b ON date_trunc('minute', b.created_at) = m.minute
            GROUP BY m.minute ORDER BY m.minute
            """, (window_minutes,)).fetchall()
    series = {k: [[int(r["ts"].timestamp()), r[k]] for r in rows] for k in ("requests", "confirmed", "failed")}
    accepted = sum(counts.get(s, 0) for s in ("HELD", "CONFIRMED", "EXPIRED"))
    processed = accepted + counts.get("FAILED", 0)
    return {
        "status": "up", "latency_ms": latency, "counts": counts,
        "seats": {"sold": seats.get("SOLD", 0), "held": seats.get("HELD", 0), "total": sum(seats.values())},
        "success_rate": round(accepted / processed * 100, 1) if processed else None,
        "series": series,
    }


# --------------------------------------------------------------------------- prometheus bundle
def prometheus_bundle(prom: Prometheus, cfg: Settings, window_minutes: int) -> dict | None:
    if not prom.enabled:
        return None
    end = time.time()
    start = end - window_minutes * 60
    step = max(5, window_minutes * 60 // 120)  # ~120 points per chart whatever the window
    apps = 'job="ticketrush-apps"'
    queries = {
        "pods": ('count by (app) (up{%s} == 1)' % apps, "app"),
        "queue": ("sum(rabbitmq_queue_messages_ready)", None),
        "rps": ('sum by (app) (rate(http_requests_total{%s,handler!~"/metrics|/healthz"}[30s]))' % apps, "app"),
        "cpu": ('avg by (app) (rate(process_cpu_seconds_total{%s}[30s]))' % apps, "app"),
        "p95": ('histogram_quantile(0.95, sum by (le) (rate(http_request_duration_highr_seconds_bucket{app="booking-service"}[1m])))', None),
        "errors": ('sum(rate(http_requests_total{%s,status="5xx"}[1m]))' % apps, None),
        "processed": ("sum by (result) (rate(worker_bookings_processed_total[30s]))", "result"),
    }
    with ThreadPoolExecutor(max_workers=len(queries)) as pool:
        futures = {k: pool.submit(prom.range, q, start, end, step) for k, (q, _) in queries.items()}
        raw = {k: f.result() for k, f in futures.items()}
    if all(v is None for v in raw.values()):
        return None  # Prometheus configured but unreachable
    data = {k: _series(raw[k], queries[k][1]) for k in queries}
    # CPU as a percentage of the pod's *request*: the exact number the HPA compares with its target.
    data["cpu"] = {app: [[ts, None if v is None else round(v / cfg.cpu_request.get(app, 0.1) * 100, 1)] for ts, v in pts]
                   for app, pts in data["cpu"].items()}
    data["events"] = scaling_events(data["pods"])
    data["step_seconds"] = step
    return data


# --------------------------------------------------------------------------- orchestration
_cache: dict = {}
_lock = threading.Lock()


def build_overview(pool, rabbit_url: str, window_minutes: int = 30, cfg: Settings | None = None) -> dict:
    cfg = cfg or Settings()
    window_minutes = max(5, min(int(window_minutes), 180))
    key = (window_minutes,)
    with _lock:  # short TTL cache: 20 open dashboards must not mean 20x the load on DB / broker / Prometheus
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < cfg.cache_ttl:
            return hit[1]

    prom = Prometheus(cfg.prometheus_url, cfg.prom_timeout)
    with ThreadPoolExecutor(max_workers=5) as ex:
        f_user = ex.submit(probe_http, "user-service", cfg.user_url, cfg.probe_timeout)
        f_catalog = ex.submit(probe_http, "catalog-service", cfg.catalog_url, cfg.probe_timeout)
        f_broker = ex.submit(probe_broker, rabbit_url)
        f_prom = ex.submit(prometheus_bundle, prom, cfg, window_minutes)
        try:
            db = database_overview(pool, window_minutes)
        except Exception as exc:
            log.exception("database overview failed")
            db = {"status": "down", "detail": type(exc).__name__, "counts": {}, "seats": {}, "series": {}}
        user, catalog, broker, metrics = f_user.result(), f_catalog.result(), f_broker.result(), f_prom.result()

    replicas = {app: _last(pts) for app, pts in (metrics or {}).get("pods", {}).items()}
    services = [
        {**user, "replicas": replicas.get("user-service")},
        {**catalog, "replicas": replicas.get("catalog-service")},
        {"name": "booking-service", "status": "up", "latency_ms": 0, "replicas": replicas.get("booking-service")},
        {"name": WORKER, "status": "up" if (broker.get("consumers") or 0) > 0 else "down",
         "replicas": replicas.get(WORKER, broker.get("consumers")), "detail": "consumers on the queue"},
    ]
    latest = lambda d: {k: _last(v) for k, v in (d or {}).items()}  # noqa: E731
    overview = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window_minutes": window_minutes,
        "environment": {"mode": "kubernetes" if metrics else "single-instance", "prometheus": bool(metrics),
                        "hpa_cpu_target": cfg.hpa_cpu_target},
        "kpis": {
            "queue_depth": broker.get("queue_depth"),
            "workers": replicas.get(WORKER, broker.get("consumers")),
            "api_pods": sum(replicas.get(a) or 0 for a in APPS) if metrics else None,
            "success_rate": db.get("success_rate"),
            "rps": round(sum(v or 0 for v in latest((metrics or {}).get("rps")).values()), 2) if metrics else None,
            "p95_seconds": _last((metrics or {}).get("p95", {}).get("all")) if metrics else None,
            "seats_sold": db.get("seats", {}).get("sold"),
        },
        "services": services,
        "infrastructure": {"database": {k: db.get(k) for k in ("status", "latency_ms", "detail")}, "broker": broker},
        "bookings": {"counts": db.get("counts", {}), "seats": db.get("seats", {}), "success_rate": db.get("success_rate")},
        "series": {"throughput": db.get("series", {}), **({k: v for k, v in metrics.items() if k != "events"} if metrics else {})},
        "scaling_events": metrics["events"] if metrics else [],
    }
    with _lock:
        _cache[key] = (time.monotonic(), overview)
    return overview
