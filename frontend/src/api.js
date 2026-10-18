// One helper for every backend call. It adds the login token automatically.
export const session = {
  token: () => localStorage.getItem("tr_token"),
  set: (t) => localStorage.setItem("tr_token", t),
  clear: () => localStorage.removeItem("tr_token"),
  user() {
    try { return JSON.parse(atob(this.token().split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).email; }
    catch { return null; }
  },
};

// Turn whatever the server sent back into a readable message.
function message(status, d) {
  if (typeof d.detail === "string") return d.detail;
  if (Array.isArray(d.detail)) return d.detail.map((x) => x.msg).join(". ");   // validation errors (422)
  if (d.error) return d.error;
  if (status === 502 || status === 503 || status === 504) return "Server is restarting. Wait a few seconds and try again.";
  return `Something went wrong (code ${status})`;
}

export async function api(path, { method = "GET", body, headers } = {}) {
  const t = session.token();
  const r = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", ...(t ? { Authorization: "Bearer " + t } : {}), ...headers },
    body: body ? JSON.stringify(body) : undefined,
  });
  const d = await r.json().catch(() => ({}));
  if (r.status === 401 && t) session.clear();
  if (!r.ok) throw new Error(message(r.status, d));
  return d;
}
