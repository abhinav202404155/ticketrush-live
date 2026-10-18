import { useCallback, useEffect, useRef, useState } from "react";
import { api, session } from "./api";

const CATS = ["All", "Movies", "Concerts", "Comedy", "Sports", "Theatre", "Workshops"];
const TZ = { timeZone: "Asia/Kolkata" };
const money = (n) => "₹" + n.toLocaleString("en-IN");
const dKey = (iso) => new Date(iso).toLocaleDateString("en-CA", TZ);
const dLabel = (iso) => new Date(iso).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", ...TZ });
const tLabel = (iso) => new Date(iso).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", ...TZ });
const hrs = (m) => `${Math.floor(m / 60)}h ${m % 60}m`;
const hueOf = (id) => (id * 83 + 20) % 360;
const grad = (id) => `radial-gradient(circle at 25% 15%, hsl(${hueOf(id)} 90% 58%), transparent 62%), linear-gradient(165deg, hsl(${(hueOf(id) + 55) % 360} 75% 26%), #0a0a10)`;
function useNow() { const [n, setN] = useState(Date.now()); useEffect(() => { const t = setInterval(() => setN(Date.now()), 1000); return () => clearInterval(t); }, []); return n; }
const secsTo = (iso, now) => Math.max(0, Math.floor((new Date(iso) - now) / 1000));
const clock = (s) => s >= 3600 ? `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m` : `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
function usePoll(fn, ms, deps) { useEffect(() => { fn(); const t = setInterval(fn, ms); return () => clearInterval(t); }, deps); }

// Original generated key-art: a different illustrated scene per category/genre, unique per event (seeded by id).
// If an event has image_url, that real image is shown instead.
const R = (id, k) => { const x = Math.sin(id * 97.1 + k * 13.7) * 1e4; return x - Math.floor(x); };
function Scene({ e }) {
  const id = e.id, h = hueOf(id), dark = `hsl(${h} 45% 7%)`, glow = `hsl(${h} 100% 72%)`, curtain = `hsl(${h} 70% 30%)`;
  const stars = [...Array(14)].map((_, i) => <circle key={i} cx={R(id, i + 5) * 100} cy={R(id, i + 30) * 75} r={R(id, i + 60) + 0.3} fill="#fff" opacity=".7" />);
  const moon = <circle cx={25 + R(id, 1) * 50} cy={30 + R(id, 2) * 20} r={14 + R(id, 3) * 8} fill={glow} opacity=".85" />;
  const ground = <rect x="0" y="120" width="100" height="30" fill={dark} />;
  const person = (x, y, s = 1) => <g key={x} fill={dark} transform={`translate(${x} ${y}) scale(${s})`}><circle cy="-34" r="5" /><path d="M-8 0L-5 -28Q0 -32 5 -28L8 0Z" /></g>;
  switch (e.category) {
    case "Movies":
      if (e.genre === "Sci-Fi") return <>{stars}<circle cx="66" cy="48" r="22" fill={glow} opacity=".9" /><ellipse cx="66" cy="48" rx="38" ry="7" fill="none" stroke="#fff" strokeOpacity=".7" strokeWidth="1.6" transform="rotate(-18 66 48)" />{ground}{person(30, 124, 1.2)}</>;
      if (e.genre === "Action") return <>{[...Array(10)].map((_, i) => <line key={i} x1={R(id, i + 1) * 110} y1="0" x2={R(id, i + 1) * 110 - 45} y2="150" stroke={glow} strokeOpacity=".28" strokeWidth="1.3" />)}{ground}{person(50, 126, 1.6)}</>;
      if (e.genre === "Family") return <>{moon}{[0, 1, 2].map((i) => <path key={i} d={`M${22 + i * 28} ${28 + i * 12}l8 10-8 10-8-10z`} fill={glow} opacity=".85" />)}{ground}{person(72, 124, 1.2)}</>;
      return <>{stars}{moon}{[...Array(9)].map((_, i) => <rect key={i} x={i * 11.5} y={95 - R(id, i + 9) * 30} width="11.5" height="70" fill={dark} />)}{person(50, 126, 1.4)}</>;
    case "Concerts":
      return <>{[0, 1, 2, 3].map((i) => <polygon key={i} points={`${14 + i * 24},0 ${i * 24 - 8},118 ${i * 24 + 36},118`} fill={glow} opacity=".17" />)}{[0, 1, 2, 3].map((i) => <circle key={i} cx={14 + i * 24} cy="3" r="4" fill="#fff" />)}<rect y="108" width="100" height="42" fill={dark} />{[...Array(18)].map((_, i) => <circle key={i} cx={i * 5.8 + 2} cy={113 + R(id, i) * 8} r="3.3" fill="#000" />)}</>;
    case "Comedy":
      return <><polygon points="40,0 60,0 90,125 10,125" fill="#fff" opacity=".18" />{ground}<rect x="48.2" y="62" width="3.6" height="60" fill={dark} /><circle cx="50" cy="58" r="6" fill={dark} />{person(28, 124, 1.2)}</>;
    case "Sports":
      return <>{[16, 84].map((x) => <g key={x}><rect x={x - 1.5} y="40" width="3" height="80" fill={dark} /><rect x={x - 8} y="30" width="16" height="10" fill={glow} /></g>)}<ellipse cx="50" cy="126" rx="60" ry="22" fill={dark} /><ellipse cx="50" cy="126" rx="46" ry="14" fill="none" stroke="#fff" strokeOpacity=".5" />
        <circle cx="50" cy="90" r="14" fill="#fff" /><path d="M50 82l7 5-3 8h-8l-3-8z" fill={dark} /></>;
    case "Theatre":
      return <><circle cx="50" cy="70" r="30" fill={glow} opacity=".25" /><circle cx="38" cy="82" r="13" fill="#f3efe6" /><circle cx="62" cy="92" r="13" fill="#f3efe6" /><path d="M32 80q3 4 6 0M42 80q3 4 6 0M56 90q3 4 6 0M66 90q3 4 6 0" stroke={dark} fill="none" strokeWidth="1.6" />
        <path d="M0 0Q34 70 14 150H0Z M100 0Q66 70 86 150H100Z" fill={curtain} /></>;
    default:
      if (e.genre === "Craft") return <>{ground}<path d="M42 72Q28 96 42 120H58Q72 96 58 72Q62 62 54 60H46Q38 62 42 72Z" fill={dark} /><ellipse cx="50" cy="121" rx="28" ry="5" fill={glow} opacity=".6" /></>;
      if (e.genre === "Photography") return <>{stars}{ground}<rect x="24" y="78" width="52" height="34" rx="5" fill={dark} /><rect x="38" y="72" width="14" height="8" fill={dark} /><circle cx="50" cy="95" r="12" fill={glow} /><circle cx="50" cy="95" r="6" fill={dark} /></>;
      return <>{moon}{ground}{person(36, 124, 1.3)}{person(64, 124, 1.3)}</>;
  }
}
function Poster({ e, mini }) {
  const cls = "poster" + (mini ? " mini" : ""), bar = !mini && e.rating != null;
  const strip = bar && <div className="pbar"><span className="star">★</span> {e.rating}/10</div>;
  if (e.image_url) return <div className={cls}><img src={e.image_url} alt={e.title} />{strip}</div>;
  return (<div className={cls} style={{ background: grad(e.id) }}>
    <svg viewBox="0 0 100 150" preserveAspectRatio="xMidYMid slice"><Scene e={e} /></svg>
    {!mini && <><span className="pcat">{e.category.toUpperCase()}</span><div className="ptxt"><b className="ptitle">{e.title}</b><small>{e.genre} · {e.language}</small></div></>}
    {strip}
  </div>);
}

function PCard({ e, go, now }) {
  const soon = new Date(e.opens_at) > now;
  return (<article className="pcard" onClick={() => go("event/" + e.id)}>
    <Poster e={e} />{soon && <span className="drop-tag">DROPS SOON</span>}
    <h4>{e.title}</h4><p className="muted small">{e.genre} · {e.language}</p>
    <p className="small">From <b>{money(e.from_price)}</b></p>
  </article>);
}

function Home({ go, city, cat, q }) {
  const [events, setEvents] = useState(null), [slide, setSlide] = useState(0), now = useNow(), [t0] = useState(Date.now());
  usePoll(() => api(`/api/events?city=${encodeURIComponent(city)}&category=${cat === "All" ? "" : cat}&q=${encodeURIComponent(q)}`).then(setEvents).catch(() => setEvents([])), 8000, [city, cat, q]);
  const filtered = q || cat !== "All", feat = (events || []).filter((e) => e.featured);
  useEffect(() => { const t = setInterval(() => setSlide((s) => s + 1), 5000); return () => clearInterval(t); }, []);
  if (!events) return <p className="muted">{now - t0 > 4000 ? "Waking up the free server… the first visit can take up to a minute. Please wait." : "Loading events…"}</p>;
  const f = feat.length ? feat[slide % feat.length] : null, soon = f && new Date(f.opens_at) > now;
  const by = (c) => events.filter((e) => e.category === c);
  return (<>
    {!filtered && f && <section className="banner" style={{ background: grad(f.id) }} key={f.id}>
      <div className="binfo"><span className="eyebrow">{soon ? "● FLASH DROP" : "● FEATURED IN " + city.toUpperCase()}</span>
        <h2 className="btitle">{f.title}</h2>
        <p className="muted">{f.genre} · {f.language} · {hrs(f.duration_min)} · <span className="star">★ {f.rating}</span></p>
        <p className="bdesc">{f.description}</p>
        <button className="btn sm" onClick={() => go("event/" + f.id)}>{soon ? `Drops in ${clock(secsTo(f.opens_at, now))}` : "Book tickets"}</button>
        <div className="dots">{feat.map((x, i) => <i key={x.id} className={x.id === f.id ? "on" : ""} onClick={() => setSlide(i)} />)}</div></div>
      <div className="bposter"><Poster e={f} /></div>
    </section>}
    {filtered ? <><h2>{events.length} result{events.length === 1 ? "" : "s"}{q && ` for “${q}”`} in {city}</h2>
      {!events.length && <p className="muted">Nothing found. Try another word, category or city.</p>}
      <div className="pgrid">{events.map((e) => <PCard key={e.id} e={e} go={go} now={now} />)}</div></>
      : <><h2>Recommended in {city}</h2><div className="scroll">{events.slice(0, 10).map((e) => <PCard key={e.id} e={e} go={go} now={now} />)}</div>
        {CATS.slice(1).map((c) => by(c).length > 0 && <div key={c}><h2>{c}</h2><div className="scroll">{by(c).map((e) => <PCard key={e.id} e={e} go={go} now={now} />)}</div></div>)}</>}
  </>);
}

function EventPage({ id, city, go }) {
  const [e, setE] = useState(null), [day, setDay] = useState(null), now = useNow();
  useEffect(() => { setE(null); api(`/api/events/${id}?city=${encodeURIComponent(city)}`).then((d) => { setE(d); setDay(d.sessions[0] ? dKey(d.sessions[0].starts_at) : null); }); }, [id, city]);
  if (!e) return <p className="muted">Loading…</p>;
  const days = [...new Set(e.sessions.map((s) => dKey(s.starts_at)))];
  const venues = {}; e.sessions.filter((s) => dKey(s.starts_at) === day).forEach((s) => (venues[s.venue] ??= []).push(s));
  return (<>
    <button className="ghost" onClick={() => go("")}>← Back</button>
    <section className="evhead"><Poster e={e} />
      <div><span className="eyebrow">{e.category.toUpperCase()}</span><h1 className="h1s">{e.title}</h1>
        <p><span className="rating">★ {e.rating}/10</span></p>
        <div className="metas"><span>{hrs(e.duration_min)}</span><span>{e.genre}</span><span>{e.language}</span><span>{e.age_rating}</span></div>
        <h3>About</h3><p className="muted">{e.description}</p></div></section>
    <h2>Select date & time <span className="muted small">· {city}</span></h2>
    {!e.sessions.length && <div className="notice">No shows in {city} yet. Try another city from the top bar.</div>}
    <div className="tabs">{days.map((d) => { const s = e.sessions.find((x) => dKey(x.starts_at) === d); return <button key={d} className={"tab" + (d === day ? " on" : "")} onClick={() => setDay(d)}>{dLabel(s.starts_at)}</button>; })}</div>
    {Object.entries(venues).map(([v, list]) => (<div className="venue" key={v}><div><b>{v}</b><p className="muted small">{city}</p></div>
      <div className="times">{list.map((s) => (<button key={s.id} className={"time" + (s.seats_available < 15 ? " fast" : "")} onClick={() => go("show/" + s.id)}>
        <b>{tLabel(s.starts_at)}</b><small>{new Date(s.opens_at) > now ? `Opens in ${clock(secsTo(s.opens_at, now))}` : `${money(s.price_inr)} · ${s.seats_available} left`}</small></button>))}</div></div>))}
  </>);
}

function ShowPage({ id, user, needLogin, go }) {
  const [show, setShow] = useState(null), [seats, setSeats] = useState([]), [sel, setSel] = useState([]);
  const [bk, setBk] = useState(null), [err, setErr] = useState(""), [busy, setBusy] = useState(false), [card, setCard] = useState("4242424242424242");
  const now = useNow();
  useEffect(() => { api("/api/shows/" + id).then(setShow); }, [id]);
  usePoll(() => api(`/api/shows/${id}/seats`).then(setSeats).catch(() => {}), 3000, [id]);
  const bid = bk?.booking_id, st = bk?.status;
  useEffect(() => { // follow the booking while it is waiting in the queue or being held
    if (!bid || !["QUEUED", "HELD"].includes(st)) return;
    const t = setInterval(() => api("/api/bookings/" + bid).then(setBk).catch(() => {}), 1000);
    return () => clearInterval(t);
  }, [bid, st]);
  if (!show) return <p className="muted">Loading…</p>;
  const open = new Date(show.opens_at) <= now, active = ["QUEUED", "HELD"].includes(st);
  const toggle = (sid) => setSel((p) => p.includes(sid) ? p.filter((x) => x !== sid) : p.length < 6 ? [...p, sid] : p);
  const act = async (fn) => { setBusy(true); setErr(""); try { await fn(); } catch (e) { setErr(e.message); } setBusy(false); };
  const reserve = () => !user ? needLogin() : act(async () => { setBk(await api("/api/bookings", { method: "POST", body: { show_id: id, seat_ids: sel } })); setSel([]); });
  const pay = () => act(async () => setBk(await api(`/api/bookings/${bid}/pay`, { method: "POST", body: { card_number: card } })));
  const rows = {}; seats.forEach((s) => (rows[s.label[0]] ??= []).push(s));
  const labels = seats.filter((s) => sel.includes(s.id)).map((s) => s.label);
  return (<>
    <button className="ghost" onClick={() => go("event/" + show.event_id)}>← Back to event</button>
    <div className="showhead"><Poster mini e={{ id: show.event_id, title: show.title, category: show.category, image_url: show.image_url }} /><div><h1 className="h1s">{show.title}</h1><p className="muted">{show.venue}, {show.city} · {dLabel(show.starts_at)}, {tLabel(show.starts_at)} · {money(show.price_inr)} per seat</p></div></div>
    {!open && <div className="notice">Booking opens in <b>{clock(secsTo(show.opens_at, now))}</b>. Get ready — the queue starts at zero.</div>}
    <div className="layout">
      <div className="map">
        <div className="stage">STAGE</div>
        {Object.entries(rows).map(([r, list]) => (<div className="row" key={r}><b>{r}</b>{list.map((s) => (
          <button key={s.id} disabled={!open || active || s.status !== "AVAILABLE"} onClick={() => toggle(s.id)}
            className={`seat ${s.status.toLowerCase()} ${sel.includes(s.id) ? "on" : ""}`}>{s.label.slice(1)}</button>))}</div>))}
        <div className="legend"><i className="seat available" />Free <i className="seat on" />Yours <i className="seat held" />Held <i className="seat sold" />Sold</div>
      </div>
      <aside className="panel">
        {!bk && <><h3>Your seats</h3>
          <p className="big">{labels.length ? labels.join(" · ") : "—"}</p>
          <p className="muted">Total</p><p className="big lime">{money(labels.length * show.price_inr)}</p>
          <button className="btn" disabled={!sel.length || !open || busy} onClick={reserve}>{busy ? "Joining…" : "Reserve seats"}</button>
          <p className="muted small">Max 6 seats. Reserved seats are held for 5 minutes.</p></>}
        {st === "QUEUED" && <div className="center"><p className="eyebrow">WAITING ROOM</p><p className="huge">#{bk.queue_position ?? "…"}</p><p className="muted">You are in the queue. Keep this tab open.</p><div className="pulse" /></div>}
        {st === "HELD" && <><p className="eyebrow">SEATS HELD · {bk.seats.join(" · ")}</p><p className="huge">{clock(secsTo(bk.expires_at, now))}</p>
          <label className="muted small">Mock card (ending 0000 is declined)</label><input value={card} onChange={(e) => setCard(e.target.value)} />
          <button className="btn" disabled={busy} onClick={pay}>Pay {money(bk.seats.length * show.price_inr)}</button></>}
        {st === "CONFIRMED" && <div className="ticket stub"><p className="eyebrow">CONFIRMED ✓</p><h3>{show.title}</h3><p className="big lime">{bk.seats.join(" · ")}</p><p className="muted small">Booking #{bk.booking_id} · demo ticket</p><button className="ghost" onClick={() => go("mine")}>My bookings</button></div>}
        {(st === "FAILED" || st === "EXPIRED") && <div className="center"><p className="eyebrow hot">{st}</p><p>{bk.reason || "Your 5-minute hold ran out."}</p><button className="btn" onClick={() => setBk(null)}>Pick seats again</button></div>}
        {err && <p className="err">{err}</p>}
      </aside>
    </div>
  </>);
}

function Mine() {
  const [rows, setRows] = useState(null);
  usePoll(() => api("/api/bookings/mine").then(setRows).catch(() => setRows([])), 5000, []);
  if (!rows) return <p className="muted">Loading…</p>;
  return (<><h2>My bookings</h2>{!rows.length && <p className="muted">Nothing yet. Go grab a seat.</p>}
    <div className="list">{rows.map((b) => (<div className="stub item" key={b.booking_id}><div><b>#{b.booking_id}</b> · Show {b.show_id}<p className="muted">{b.seats.join(", ")}</p></div><span className={`pill ${b.status}`}>{b.status}</span></div>))}</div></>);
}

function Control() {
  const [key, setKey] = useState(localStorage.getItem("tr_admin") || "admin-demo-key"), [s, setS] = useState(null), [e, setE] = useState(""), [log, setLog] = useState([]), prev = useRef(null);
  usePoll(() => api("/api/admin/stats", { headers: { "X-Admin-Key": key } }).then((d) => {
    setS(d); setE(""); localStorage.setItem("tr_admin", key);
    const w = d.pods?.["booking-worker"];   // log every change in worker count while this page is open
    if (w != null) { if (prev.current != null && w !== prev.current) setLog((l) => [{ t: new Date().toLocaleTimeString("en-IN"), m: `Workers ${prev.current} → ${w}`, up: w > prev.current }, ...l].slice(0, 10)); prev.current = w; }
  }).catch((x) => setE(x.message)), 2000, [key]);
  const c = s?.counts || {}, total = Math.max(1, Object.values(c).reduce((a, b) => a + b, 0)), pods = s?.pods;
  const apiPods = pods ? ["user-service", "catalog-service", "booking-service"].reduce((n, k) => n + (pods[k] || 0), 0) : null;
  return (<><h2>Control Room <span className="live">● LIVE</span></h2>
    <label className="muted small">Admin key </label><input className="inline" value={key} onChange={(x) => setKey(x.target.value)} />{e && <p className="err">{e}</p>}
    <div className="tiles">
      <div className="tile"><small>QUEUE LENGTH</small><b>{s ? s.queue_length : "–"}</b></div>
      <div className="tile"><small>SUCCESS RATE</small><b>{s?.success_rate != null ? s.success_rate + "%" : "–"}</b></div>
      <div className="tile"><small>SEATS SOLD</small><b>{s ? s.seats_sold : "–"}</b></div>
      <div className="tile"><small>WORKER PODS</small><b>{pods ? pods["booking-worker"] ?? 0 : "n/a"}</b>{!pods && <span className="muted small">needs Kubernetes + Prometheus</span>}</div>
      <div className="tile"><small>API PODS</small><b>{apiPods ?? "n/a"}</b></div>
    </div>
    <div className="bars">{["QUEUED", "HELD", "CONFIRMED", "FAILED", "EXPIRED"].map((k) => (<div key={k} className="bar"><span>{k}</span><div><i className={k} style={{ width: ((c[k] || 0) / total) * 100 + "%" }} /></div><b>{c[k] || 0}</b></div>))}</div>
    <h3 className="evh">Scaling events <span className="muted small">(while this page is open)</span></h3>
    <div className="evlog">{!log.length && <p className="muted small">No change yet. Start a load test and watch.</p>}{log.map((x, i) => <p key={i} className={x.up ? "up" : "down"}><b>{x.t}</b> {x.m}</p>)}</div></>);
}

function Auth({ onDone, onClose }) {
  const [mode, setMode] = useState("login"), [email, setEmail] = useState(""), [pw, setPw] = useState(""), [err, setErr] = useState("");
  const submit = async () => { setErr(""); try {
    if (mode === "signup") await api("/api/users/signup", { method: "POST", body: { email, password: pw } });
    const r = await api("/api/users/login", { method: "POST", body: { email, password: pw } });
    session.set(r.access_token); onDone();
  } catch (x) { setErr(x.message); } };
  return (<div className="overlay" onClick={onClose}><div className="modal" onClick={(x) => x.stopPropagation()}>
    <h3>{mode === "login" ? "Welcome back" : "Create account"}</h3>
    <p className="notice">Demo project. Do not use a real password.</p>
    <input placeholder="Email" value={email} onChange={(x) => setEmail(x.target.value)} />
    <input placeholder="Password (min 8)" type="password" value={pw} onChange={(x) => setPw(x.target.value)} />
    {err && <p className="err">{err}</p>}
    <button className="btn" onClick={submit}>{mode === "login" ? "Log in" : "Sign up"}</button>
    <button className="ghost" onClick={() => setMode(mode === "login" ? "signup" : "login")}>{mode === "login" ? "New here? Sign up" : "Have an account? Log in"}</button>
  </div></div>);
}

export default function App() {
  const route = () => location.hash.replace(/^#\/?/, "").split("/");
  const [r, setR] = useState(route()), [user, setUser] = useState(session.user()), [auth, setAuth] = useState(false);
  const [city, setCity] = useState(localStorage.getItem("tr_city") || "Mumbai"), [cities, setCities] = useState([city]);
  const [cat, setCat] = useState("All"), [q, setQ] = useState("");
  useEffect(() => { const f = () => setR(route()); addEventListener("hashchange", f); api("/api/cities").then(setCities).catch(() => {}); return () => removeEventListener("hashchange", f); }, []);
  const go = (p) => { location.hash = "#/" + p; window.scrollTo(0, 0); };
  const gate = (el) => user ? el : <div className="notice">Please <button className="link" onClick={() => setAuth(true)}>log in</button> first.</div>;
  const home = r[0] === "";
  return (<>
    <nav className="nav">
      <div className="brand" onClick={() => { setQ(""); setCat("All"); go(""); }}><b className="logo">TICKET<span>RUSH</span></b><small>Every seat. One owner.</small></div>
      <input className="search" placeholder="Search movies, concerts, comedy, venues…" value={q} onChange={(x) => { setQ(x.target.value); if (!home) go(""); }} />
      <select className="sel" value={city} onChange={(x) => { setCity(x.target.value); localStorage.setItem("tr_city", x.target.value); }}>{cities.map((c) => <option key={c}>{c}</option>)}</select>
      <div className="links"><button onClick={() => go("mine")}>My bookings</button><button onClick={() => go("control")}>Control Room</button></div>
      {user ? <button className="ghost" onClick={() => { session.clear(); setUser(null); }}>Log out</button> : <button className="btn sm" onClick={() => setAuth(true)}>Log in</button>}
    </nav>
    {home && <div className="chips">{CATS.map((c) => <button key={c} className={"chip" + (c === cat ? " on" : "")} onClick={() => setCat(c)}>{c}</button>)}</div>}
    <main>
      {home && <Home go={go} city={city} cat={cat} q={q} />}
      {r[0] === "event" && <EventPage id={Number(r[1])} city={city} go={go} />}
      {r[0] === "show" && <ShowPage id={Number(r[1])} user={user} needLogin={() => setAuth(true)} go={go} />}
      {r[0] === "mine" && gate(<Mine />)}
      {r[0] === "control" && <Control />}
    </main>
    <footer><b>Every seat. One owner.</b><br />Sample events are fictional · mock payments only · do not use real passwords</footer>
    {auth && <Auth onClose={() => setAuth(false)} onDone={() => { setUser(session.user()); setAuth(false); }} />}
  </>);
}
