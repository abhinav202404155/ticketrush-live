import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";

/**
 * Polls /api/admin/overview.
 * - pauses while the browser tab is hidden (no wasted requests, no needless wake-ups of free-tier servers)
 * - never overlaps two requests
 * - keeps the last good data on screen if one poll fails, and backs off (2x, max 30s) until it recovers
 */
export function useOverview({ adminKey, windowMinutes, intervalMs = 3000, paused = false }) {
  const [state, setState] = useState({ data: null, error: "", loading: true, updatedAt: null });
  const busy = useRef(false);

  const load = useCallback(async () => {
    if (busy.current) return false;
    busy.current = true;
    try {
      const data = await api(`/api/admin/overview?window=${windowMinutes}`, { headers: { "X-Admin-Key": adminKey } });
      setState({ data, error: "", loading: false, updatedAt: Date.now() });
      return true;
    } catch (e) {
      setState((s) => ({ ...s, error: e.message, loading: false }));
      return false;
    } finally {
      busy.current = false;
    }
  }, [adminKey, windowMinutes]);

  useEffect(() => {
    if (paused) return undefined;
    let timer, delay = intervalMs, stopped = false;
    const tick = async () => {
      if (stopped) return;
      if (!document.hidden) {
        const ok = await load();
        delay = ok ? intervalMs : Math.min(delay * 2, 30000);
      }
      timer = setTimeout(tick, delay);
    };
    tick();
    const onVisible = () => { if (!document.hidden) { clearTimeout(timer); tick(); } };
    document.addEventListener("visibilitychange", onVisible);
    return () => { stopped = true; clearTimeout(timer); document.removeEventListener("visibilitychange", onVisible); };
  }, [load, intervalMs, paused]);

  return { ...state, refresh: load };
}
