"""Unit tests for the dashboard backend. They need no running stack: Prometheus, the DB and
the broker are replaced by small fakes. Run:  python -m pytest tests/test_dashboard_overview.py -v"""
import json
import os
import sys
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

os.environ.update(DATABASE_URL="postgresql://x:x@localhost/x", RABBITMQ_URL="amqp://x:x@localhost:1/",
                  JWT_SECRET="test-secret-0123456789abcdef0123456789", ADMIN_KEY="test-admin-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "booking-service"))

from app import observability as obs  # noqa: E402


def test_nan_and_inf_become_none():
    assert obs._num("NaN") is None and obs._num("+Inf") is None and obs._num("x") is None
    assert obs._num("3.5") == 3.5


def test_scaling_events_detects_up_and_down_newest_first():
    pods = {"booking-worker": [[100, 1.0], [115, 1.0], [130, 4.0], [145, 4.0], [160, 2.0]],
            "user-service": [[100, 1.0], [160, 1.0]]}
    events = obs.scaling_events(pods)
    assert [(e["app"], e["from"], e["to"], e["direction"]) for e in events] == [
        ("booking-worker", 4, 2, "down"), ("booking-worker", 1, 4, "up")]


def test_scaling_events_ignores_gaps():
    assert obs.scaling_events({"a": [[1, 1.0], [2, None], [3, 1.0]]}) == []


class FakeProm(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        q = self.path
        now = 1_700_000_000
        if "count+by+%28app%29" in q or "count%20by%20%28app%29" in q:
            result = [{"metric": {"app": "booking-worker"}, "values": [[now, "1"], [now + 15, "3"]]}]
        elif "process_cpu_seconds_total" in q:
            result = [{"metric": {"app": "booking-service"}, "values": [[now, "0.07"]]}]
        elif "histogram_quantile" in q:
            result = [{"metric": {}, "values": [[now, "NaN"]]}]
        else:
            result = []
        body = json.dumps({"status": "success", "data": {"resultType": "matrix", "result": result}}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


@pytest.fixture()
def prom_server():
    srv = HTTPServer(("127.0.0.1", 0), FakeProm)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_prometheus_bundle_scales_cpu_to_hpa_percent_and_derives_events(prom_server):
    cfg = obs.Settings(prometheus_url=prom_server)
    data = obs.prometheus_bundle(obs.Prometheus(prom_server, 2), cfg, 30)
    assert data["cpu"]["booking-service"][0][1] == 70.0          # 0.07 cores / 0.1 request = 70 %
    assert data["p95"]["all"][0][1] is None                      # NaN sanitised
    assert data["events"][0]["to"] == 3 and data["events"][0]["direction"] == "up"


def test_prometheus_down_means_single_instance_mode():
    assert obs.prometheus_bundle(obs.Prometheus("http://127.0.0.1:1", 0.5), obs.Settings(prometheus_url="http://127.0.0.1:1"), 30) is None
    assert obs.prometheus_bundle(obs.Prometheus("", 1), obs.Settings(), 30) is None


class FakePool:
    """Mimics pool.connection() as conn with execute().fetchall()/fetchone()."""
    def connection(self):
        return self
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def execute(self, sql, params=None):
        self._sql = sql
        return self
    def fetchall(self):
        if "FROM bookings GROUP BY status" in self._sql:
            return [{"status": "CONFIRMED", "n": 8}, {"status": "FAILED", "n": 2}]
        if "FROM seats GROUP BY status" in self._sql:
            return [{"status": "SOLD", "n": 8}, {"status": "AVAILABLE", "n": 92}]
        t = datetime(2026, 10, 19, tzinfo=timezone.utc)
        return [{"ts": t + timedelta(minutes=i), "requests": i, "confirmed": i // 2, "failed": 0} for i in range(3)]


def test_overview_in_single_instance_mode(monkeypatch):
    obs._cache.clear()
    monkeypatch.setattr(obs, "probe_http", lambda name, url, t: {"name": name, "status": "up", "latency_ms": 12})
    monkeypatch.setattr(obs, "probe_broker", lambda url: {"name": "rabbitmq", "status": "up", "queue_depth": 4, "consumers": 1, "latency_ms": 5})
    o = obs.build_overview(FakePool(), "amqp://x", 30, obs.Settings(prometheus_url=""))
    assert o["environment"]["mode"] == "single-instance"
    assert o["kpis"]["queue_depth"] == 4 and o["kpis"]["success_rate"] == 80.0 and o["kpis"]["api_pods"] is None
    assert o["scaling_events"] == [] and len(o["series"]["throughput"]["requests"]) == 3
    assert {s["name"] for s in o["services"]} == {"user-service", "catalog-service", "booking-service", "booking-worker"}


def test_overview_window_is_clamped_and_cached(monkeypatch):
    obs._cache.clear()
    calls = []
    monkeypatch.setattr(obs, "probe_http", lambda n, u, t: calls.append(n) or {"name": n, "status": "up", "latency_ms": 1})
    monkeypatch.setattr(obs, "probe_broker", lambda url: {"name": "rabbitmq", "status": "down", "queue_depth": None, "consumers": None})
    cfg = obs.Settings(prometheus_url="", cache_ttl=60)
    assert obs.build_overview(FakePool(), "amqp://x", 99999, cfg)["window_minutes"] == 180
    obs.build_overview(FakePool(), "amqp://x", 99999, cfg)
    assert len(calls) == 2  # second call served from cache


def test_endpoint_requires_admin_key(monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    monkeypatch.setattr(main.observability, "build_overview", lambda *a, **k: {"ok": True})
    c = TestClient(main.app)
    assert c.get("/api/admin/overview").status_code == 401
    assert c.get("/api/admin/overview", headers={"X-Admin-Key": "wrong"}).status_code == 401
    assert c.get("/api/admin/overview", headers={"X-Admin-Key": "test-admin-key"}).json() == {"ok": True}
