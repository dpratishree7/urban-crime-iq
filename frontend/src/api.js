// Every call to the backend lives in this one file.
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function qs(params = {}) {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    (Array.isArray(value) ? value : [value]).forEach((v) => {
      if (v !== undefined && v !== null && v !== "") p.append(key, v);
    });
  });
  const s = p.toString();
  return s ? `?${s}` : "";
}

function niceError(body, status) {
  const detail = body && body.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((e) => {
        const field = (e.loc || []).filter((x) => x !== "body" && x !== "query").join(" / ");
        return field ? `${field}: ${e.msg}` : e.msg;
      })
      .join("; ");
  }
  return `The server returned an error (${status}).`;
}

async function request(path, { method = "GET", params, body } = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}${qs(params)}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error(
      "Cannot reach the API. Start it with: cd backend, then uvicorn app.main:app --reload"
    );
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* no JSON body */
  }
  if (!res.ok) throw new Error(niceError(data, res.status));
  return data;
}

export const api = {
  meta: () => request("/api/meta"),
  summary: () => request("/api/summary"),
  rollup: (level, filters) => request("/api/olap/rollup", { params: { level, ...filters } }),
  drilldown: (hierarchy, level, value, filters) =>
    request("/api/olap/drilldown", { params: { hierarchy, level, value, ...filters } }),
  slice: (filters) => request("/api/olap/slice", { params: filters }),
  topAreas: (filters, limit = 10, minPopulation = 0) =>
    request("/api/olap/top-areas", { params: { limit, min_population: minPopulation, ...filters } }),
  heatmap: (filters) => request("/api/olap/heatmap", { params: filters }),
  hotspots: () => request("/api/hotspots"),
  lookup: (body) => request("/api/hotspots/lookup", { method: "POST", body }),
  forecast: (body) => request("/api/forecast", { method: "POST", body }),
  violence: (body) => request("/api/predict/violence", { method: "POST", body }),
  patterns: (params) => request("/api/patterns", { params }),
};
