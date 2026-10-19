import { useState } from "react";
import LineChart from "./LineChart";
import { useOverview } from "./useOverview";
import "./dashboard.css";

const PALETTE = { "user-service": "#4cc9f0", "catalog-service": "#b388ff", "booking-service": "#d6ff3d", "booking-worker": "#ffb02e" };
const STATUS_COLOR = { QUEUED: "#ffb02e", HELD: "#4cc9f0", CONFIRMED: "#d6ff3d", FAILED: "#ff5a3c", EXPIRED: "#8d8a84" };
const WINDOWS = [[15, "15 min"], [30, "30 min"], [60, "1 hour"], [180, "3 hours"]];
const FLOW = ["frontend", "user-service", "catalog-service", "booking-service", "rabbitmq", "booking-worker", "postgres"];

const num = (v, d = 0) => (v == null ? "–" : Number(v).toFixed(d));
const byApp = (map = {}, names = Object.keys(PALETTE)) =>
  names.filter((n) => map[n]).map((n) => ({ name: n, color: PALETTE[n], points: map[n] }));

function Kpi({ label, value, hint, tone }) {
  return (<div className={"db-kpi" + (tone ? " " + tone : "")}><small>{label}</small><b>{value}</b>{hint && <span>{hint}</span>}</div>);
}

function ServiceCard({ s }) {
  const up = s.status === "up";
  return (
    <div className={"db-svc " + (up ? "up" : "down")}>
      <div><i className="db-dot" aria-hidden /> <b>{s.name}</b></div>
      <p>{up ? "Healthy" : "Unreachable"}{s.latency_ms ? ` · ${s.latency_ms} ms` : ""}</p>
      {s.replicas != null && <p className="muted">{s.replicas} {s.replicas === 1 ? "replica" : "replicas"}</p>}
      {!up && s.detail && <p className="muted small">{s.detail}</p>}
    </div>
  );
}

function Funnel({ counts = {} }) {
  const total = Math.max(1, Object.values(counts).reduce((a, b) => a + b, 0));
  return (
    <div className="db-funnel">
      {Object.keys(STATUS_COLOR).map((k) => (
        <div key={k} className="db-frow">
          <span>{k}</span>
          <div><i style={{ width: `${((counts[k] || 0) / total) * 100}%`, background: STATUS_COLOR[k] }} /></div>
          <b>{counts[k] || 0}</b>
        </div>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const [adminKey, setAdminKey] = useState(localStorage.getItem("tr_admin") || "");
  const [draftKey, setDraftKey] = useState(adminKey);
  const [windowMinutes, setWindowMinutes] = useState(30);
  const [paused, setPaused] = useState(false);
  const { data, error, loading, updatedAt, refresh } = useOverview({ adminKey, windowMinutes, paused });

  const unlock = (e) => { e.preventDefault(); localStorage.setItem("tr_admin", draftKey.trim()); setAdminKey(draftKey.trim()); };
  const needKey = error && /admin key/i.test(error);

  if (needKey || (!data && !adminKey)) {
    return (
      <section className="db">
        <h2>Control Room</h2>
        <form className="db-lock" onSubmit={unlock}>
          <label htmlFor="adminKey">Enter the admin key to open the dashboard</label>
          <input id="adminKey" type="password" autoComplete="off" value={draftKey} onChange={(e) => setDraftKey(e.target.value)} placeholder="ADMIN_KEY" />
          {needKey && <p className="err">That key was not accepted.</p>}
          <button className="btn sm" type="submit">Open dashboard</button>
        </form>
      </section>
    );
  }
  if (!data) return <section className="db"><h2>Control Room</h2><p className="muted">{error || (loading ? "Loading…" : "")}</p>{error && <p className="muted small">If the server was asleep, wait about a minute; this page retries by itself.</p>}</section>;

  const { kpis, environment: env, services, infrastructure: infra, series, scaling_events: events, bookings } = data;
  const k8s = env.mode === "kubernetes";
  const stale = error ? "Connection problem, showing last data" : "";
  const nodes = {
    ...Object.fromEntries(services.map((s) => [s.name, s])),
    rabbitmq: { name: "rabbitmq", ...infra.broker, detail: infra.broker.queue_depth != null ? `${infra.broker.queue_depth} waiting` : infra.broker.detail },
    postgres: { name: "postgres", ...infra.database },
    frontend: { name: "frontend", status: "up", latency_ms: null },
  };
  const cpuSeries = byApp(series.cpu);
  const processed = Object.entries(series.processed || {}).map(([name, points]) => ({ name, color: STATUS_COLOR[name] || "#8d8a84", points }));

  return (
    <section className="db">
      <header className="db-head">
        <div>
          <h2>Control Room <span className="live" aria-live="polite">{paused ? "❚❚ PAUSED" : "● LIVE"}</span></h2>
          <p className="muted small">
            Updated {updatedAt ? new Date(updatedAt).toLocaleTimeString("en-IN") : "–"} {stale && <b className="err">· {stale}</b>}
          </p>
        </div>
        <div className="db-tools">
          <span className={"db-badge " + (k8s ? "k8s" : "single")} title={k8s ? "Prometheus connected" : "No Prometheus: single instance"}>{k8s ? "Kubernetes · autoscaling on" : "Single instance · no autoscaler"}</span>
          <select aria-label="Time window" value={windowMinutes} onChange={(e) => setWindowMinutes(Number(e.target.value))}>{WINDOWS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
          <button className="ghost" onClick={() => setPaused((p) => !p)}>{paused ? "Resume" : "Pause"}</button>
          <button className="ghost" onClick={refresh}>Refresh</button>
        </div>
      </header>

      <div className="db-kpis">
        <Kpi label="QUEUE DEPTH" value={num(kpis.queue_depth)} hint="bookings waiting" tone={kpis.queue_depth > 50 ? "warn" : ""} />
        <Kpi label="WORKERS" value={num(kpis.workers)} hint={k8s ? "KEDA scales on queue" : "consumers on queue"} />
        <Kpi label="API PODS" value={k8s ? num(kpis.api_pods) : "n/a"} hint={k8s ? "HPA scales on CPU" : "needs Kubernetes"} />
        <Kpi label="SUCCESS RATE" value={kpis.success_rate != null ? num(kpis.success_rate, 1) + "%" : "–"} hint="seat won / processed" />
        <Kpi label="REQUESTS / SEC" value={k8s ? num(kpis.rps, 1) : "n/a"} hint="all APIs" />
        <Kpi label="BOOKING P95" value={k8s && kpis.p95_seconds != null ? Math.round(kpis.p95_seconds * 1000) + " ms" : "n/a"} hint="latency" />
        <Kpi label="SEATS SOLD" value={num(kpis.seats_sold)} hint={`of ${num(bookings.seats.total)}`} />
      </div>

      <h3 className="db-h">Microservices <span className="muted small">request path: frontend → APIs → queue → workers → database</span></h3>
      <div className="db-flow">{FLOW.map((n) => <ServiceCard key={n} s={nodes[n]} />)}</div>

      <h3 className="db-h">Autoscaling</h3>
      {!k8s && <p className="db-note">Autoscaling charts appear when the stack runs on Kubernetes with Prometheus (HPA scales the APIs on CPU, KEDA scales workers on queue length). This deployment runs one instance per service, so only health, queue and booking data are available here.</p>}
      <div className="db-grid">
        <LineChart title="Replicas over time" series={[...byApp(series.pods)]} stepped emptyText="Needs Kubernetes + Prometheus" />
        <LineChart title="Queue depth" series={series.queue ? [{ name: "waiting", color: "#ffb02e", points: series.queue.all }] : []} area emptyText="Needs Kubernetes + Prometheus" />
        <LineChart title={`CPU vs HPA target (${env.hpa_cpu_target}% of request)`} series={cpuSeries} unit="%" threshold={{ value: env.hpa_cpu_target, label: "HPA target" }} emptyText="Needs Kubernetes + Prometheus" />
        <LineChart title="Requests per second" series={byApp(series.rps, Object.keys(PALETTE).slice(0, 3))} decimals={1} emptyText="Needs Kubernetes + Prometheus" />
        <LineChart title="Booking-service p95 latency" series={series.p95 ? [{ name: "p95", color: "#d6ff3d", points: series.p95.all.map(([t, v]) => [t, v == null ? null : v * 1000]) }] : []} unit=" ms" emptyText="Needs Kubernetes + Prometheus" />
        <LineChart title="Bookings processed per second" series={processed} decimals={2} emptyText="Needs Kubernetes + Prometheus" />
      </div>

      <h3 className="db-h">Scaling events <span className="muted small">last {data.window_minutes} min</span></h3>
      <div className="db-events">
        {!events.length && <p className="muted small">{k8s ? "No scaling in this window. Run the Locust rush to trigger it." : "Not available without Kubernetes."}</p>}
        {events.map((e, i) => (
          <p key={i} className={e.direction}><b>{new Date(e.ts * 1000).toLocaleTimeString("en-IN")}</b> {e.app} scaled {e.direction} <span>{e.from} → {e.to}</span></p>
        ))}
      </div>

      <h3 className="db-h">Bookings</h3>
      <div className="db-grid">
        <LineChart title="Booking requests per minute" series={[
          { name: "requests", color: "#4cc9f0", points: series.throughput.requests || [] },
          { name: "confirmed", color: "#d6ff3d", points: series.throughput.confirmed || [] },
          { name: "failed", color: "#ff5a3c", points: series.throughput.failed || [] }]} />
        <div className="dbc"><figcaption>Status of all bookings</figcaption><Funnel counts={bookings.counts} /></div>
      </div>
    </section>
  );
}
