import { useMemo, useState } from "react";

const W = 640, H = 220, PAD = { t: 12, r: 14, b: 26, l: 46 };
const fmtTime = (ts) => new Date(ts * 1000).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false });
const tick = (v) => (Number.isInteger(v) ? String(v) : v.toFixed(1));
const niceMax = (v) => {
  if (!(v > 0)) return 1;
  const p = 10 ** Math.floor(Math.log10(v)), n = v / p;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p;
};

/**
 * Dependency-free SVG line chart.
 *  series:    [{ name, color, points: [[unixSeconds, number|null], ...] }]
 *  stepped:   draw as steps (right for integer counts such as pod replicas)
 *  threshold: { value, label } draws a dashed reference line (e.g. the HPA CPU target)
 *  area:      fill under the first series
 */
export default function LineChart({ title, series, unit = "", stepped = false, threshold, area = false, decimals = 0, emptyText = "No data yet" }) {
  const [hover, setHover] = useState(null);
  const model = useMemo(() => {
    const live = series.filter((s) => s.points.some(([, v]) => v != null));
    if (!live.length) return null;
    const all = live.flatMap((s) => s.points);
    const xs = all.map(([t]) => t), x0 = Math.min(...xs), x1 = Math.max(...xs);
    const yMax = niceMax(Math.max(...all.map(([, v]) => v ?? 0), threshold?.value ?? 0) * 1.1);
    const sx = (t) => PAD.l + ((t - x0) / Math.max(1, x1 - x0)) * (W - PAD.l - PAD.r);
    const sy = (v) => H - PAD.b - (v / yMax) * (H - PAD.t - PAD.b);
    const paths = live.map((s) => {
      let d = "", prev = null;
      for (const [t, v] of s.points) {
        if (v == null) { prev = null; continue; }
        d += prev == null ? `M${sx(t).toFixed(1)},${sy(v).toFixed(1)}` : stepped ? `H${sx(t).toFixed(1)}V${sy(v).toFixed(1)}` : `L${sx(t).toFixed(1)},${sy(v).toFixed(1)}`;
        prev = v;
      }
      return { ...s, d };
    });
    return { live, paths, x0, x1, yMax, sx, sy, times: [...new Set(xs)].sort((a, b) => a - b) };
  }, [series, stepped, threshold]);

  const onMove = (e) => {
    if (!model) return;
    const box = e.currentTarget.getBoundingClientRect();
    const t = model.x0 + ((e.clientX - box.left) / box.width * W - PAD.l) / (W - PAD.l - PAD.r) * (model.x1 - model.x0);
    setHover(model.times.reduce((a, b) => (Math.abs(b - t) < Math.abs(a - t) ? b : a)));
  };
  const valueAt = (s, t) => s.points.find(([ts]) => ts === t)?.[1];
  const fmt = (v) => (v == null ? "–" : v.toFixed(decimals) + unit);

  return (
    <figure className="dbc" aria-label={title}>
      <figcaption>{title}</figcaption>
      {!model ? <p className="muted small dbc-empty">{emptyText}</p> : (
        <>
          <div className="dbc-legend">{model.live.map((s) => <span key={s.name}><i style={{ background: s.color }} />{s.name}</span>)}</div>
          <svg viewBox={`0 0 ${W} ${H}`} role="img" onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
            {[0, 0.25, 0.5, 0.75, 1].map((f) => (
              <g key={f}>
                <line x1={PAD.l} x2={W - PAD.r} y1={model.sy(model.yMax * f)} y2={model.sy(model.yMax * f)} className="dbc-grid" />
                <text x={PAD.l - 6} y={model.sy(model.yMax * f) + 4} className="dbc-axis" textAnchor="end">{tick(model.yMax * f)}{unit}</text>
              </g>
            ))}
            {[0, 0.5, 1].map((f) => <text key={f} x={PAD.l + f * (W - PAD.l - PAD.r)} y={H - 6} className="dbc-axis" textAnchor={f === 0 ? "start" : f === 1 ? "end" : "middle"}>{fmtTime(model.x0 + f * (model.x1 - model.x0))}</text>)}
            {threshold && <g><line x1={PAD.l} x2={W - PAD.r} y1={model.sy(threshold.value)} y2={model.sy(threshold.value)} className="dbc-threshold" /><text x={W - PAD.r} y={model.sy(threshold.value) - 5} className="dbc-axis" textAnchor="end">{threshold.label}</text></g>}
            {area && <path d={`${model.paths[0].d}L${model.sx(model.x1)},${model.sy(0)}L${model.sx(model.x0)},${model.sy(0)}Z`} fill={model.paths[0].color} opacity=".12" />}
            {model.paths.map((s) => <path key={s.name} d={s.d} fill="none" stroke={s.color} strokeWidth="2" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />)}
            {hover != null && <line x1={model.sx(hover)} x2={model.sx(hover)} y1={PAD.t} y2={H - PAD.b} className="dbc-cursor" />}
          </svg>
          {hover != null && <div className="dbc-tip"><b>{fmtTime(hover)}</b>{model.live.map((s) => <span key={s.name}><i style={{ background: s.color }} />{s.name}: {fmt(valueAt(s, hover))}</span>)}</div>}
        </>
      )}
    </figure>
  );
}
