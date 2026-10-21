import { Fragment, useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api.js";
import { useApi } from "../useApi.js";
import { useMeta } from "../MetaContext.jsx";
import { Case, ErrorBox, Field, Spinner, Stat, Tape, fmt, title } from "../components/Ui.jsx";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const TIME_LEVELS = ["year", "month", "day", "hour"];
const PLACE_LEVELS = ["district", "beat"];
const LEVEL_TITLE = {
  year: "Crimes per year",
  month: "Crimes per month",
  day: "Crimes per day",
  hour: "Crimes per hour of the day",
  district: "Crimes per police district",
  beat: "Crimes per beat",
};
const EMPTY = { year: "", month: "", district: "", crime_type: "", season: "" };
const TICK = { fill: "#9a97a3", fontSize: 12 };
const TIP = { background: "#141418", border: "1px solid #3a3a44", color: "#e7e2d6" };

const toParams = (f) => Object.fromEntries(Object.entries(f).filter(([, v]) => v !== ""));

function DrillChart({ filters }) {
  const [hierarchy, setHierarchy] = useState("time");
  const [trail, setTrail] = useState([]);
  const levels = hierarchy === "time" ? TIME_LEVELS : PLACE_LEVELS;
  const level = levels[trail.length];
  const canDrill = trail.length < levels.length - 1;
  const fkey = JSON.stringify(filters);

  useEffect(() => setTrail([]), [fkey]);

  const { data, error, loading, reload } = useApi(() => {
    const last = trail[trail.length - 1];
    if (hierarchy === "time") {
      return last ? api.drilldown("time", last.level, last.value, filters) : api.rollup("year", filters);
    }
    return last
      ? api.drilldown("place", last.level, last.value, filters)
      : api.drilldown("place", "city", "", filters);
  }, [fkey, hierarchy, JSON.stringify(trail)]);

  const rows = data?.rows ?? [];
  const peak = Math.max(0, ...rows.map((r) => r.crimes));
  const onBar = (label) => {
    if (canDrill && label !== undefined) setTrail([...trail, { level, value: label }]);
  };
  const switchTo = (h) => {
    setHierarchy(h);
    setTrail([]);
  };
  const crumb = (t) => (t.level === "district" ? `District ${t.value}` : t.value);
  const colour = (r) =>
    level === "hour" && (r.label === "0" || r.label === "12")
      ? "#7a2b31"
      : r.crimes === peak
      ? "#e5383b"
      : "#f2a33a";

  return (
    <Case
      title={LEVEL_TITLE[level]}
      tag="Roll-up and drill-down"
      right={
        <div className="seg" role="group" aria-label="Choose a hierarchy">
          <button className={hierarchy === "time" ? "on" : ""} onClick={() => switchTo("time")}>
            By time
          </button>
          <button className={hierarchy === "place" ? "on" : ""} onClick={() => switchTo("place")}>
            By place
          </button>
        </div>
      }
    >
      <nav className="crumbs" aria-label="Drill-down path">
        <button className={trail.length === 0 ? "on" : ""} onClick={() => setTrail([])}>
          {hierarchy === "time" ? "All years" : "Whole city"}
        </button>
        {trail.map((t, i) => (
          <span key={i}>
            <span aria-hidden="true"> / </span>
            <button className={i === trail.length - 1 ? "on" : ""} onClick={() => setTrail(trail.slice(0, i + 1))}>
              {crumb(t)}
            </button>
          </span>
        ))}
      </nav>
      {error && <ErrorBox message={error} onRetry={reload} />}
      {loading && !data && <Spinner />}
      {data && (
        <>
          <div className={loading ? "dim" : ""}>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
                <CartesianGrid stroke="#26262c" vertical={false} />
                <XAxis dataKey="label" tick={TICK} interval={rows.length > 24 ? 1 : 0} />
                <YAxis tick={TICK} width={62} tickFormatter={(v) => fmt(v)} />
                <Tooltip cursor={{ fill: "rgba(242,163,58,0.08)" }} contentStyle={TIP} formatter={(v) => [fmt(v), "Crimes"]} />
                <Bar
                  dataKey="crimes"
                  cursor={canDrill ? "pointer" : "default"}
                  onClick={(d) => onBar(d?.payload?.label ?? d?.label)}
                >
                  {rows.map((r, i) => (
                    <Cell key={i} fill={colour(r)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="hint">
            {canDrill
              ? `Click a bar to go one level down, from ${level} to ${levels[trail.length + 1]}.`
              : "This is the lowest level. Use the path above to go back up."}
            {level === "hour" &&
              " Hours 0 and 12 (dark red) include reports stamped with a default time, so they run high."}
          </p>
        </>
      )}
    </Case>
  );
}

function TopAreas({ filters }) {
  const [small, setSmall] = useState(false);
  const { data, error, loading, reload } = useApi(
    () => api.topAreas(filters, 10, small ? 10000 : 0),
    [JSON.stringify(filters), small]
  );
  const rows = data?.rows ?? [];
  return (
    <Case
      title="Areas with the most crime per 1,000 residents"
      tag="Rate, not count"
      right={
        <label className="check">
          <input type="checkbox" checked={small} onChange={(e) => setSmall(e.target.checked)} />
          Hide areas under 10,000 residents
        </label>
      }
    >
      {error && <ErrorBox message={error} onRetry={reload} />}
      {loading && !data && <Spinner />}
      {data && (
        <>
          <div className={loading ? "dim" : ""}>
            <ResponsiveContainer width="100%" height={340}>
              <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 4 }}>
                <CartesianGrid stroke="#26262c" horizontal={false} />
                <XAxis type="number" tick={TICK} />
                <YAxis type="category" dataKey="area_name" tick={TICK} width={150} />
                <Tooltip
                  cursor={{ fill: "rgba(200,32,47,0.1)" }}
                  contentStyle={TIP}
                  formatter={(v, n, p) => [`${v} per 1,000 (${fmt(p.payload.crimes)} crimes, ${fmt(p.payload.population)} residents)`, "Rate"]}
                />
                <Bar dataKey="crimes_per_1000" fill="#c8202f" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="hint">
            Downtown areas such as the Loop rank high because few people live there while many visit.
          </p>
        </>
      )}
    </Case>
  );
}

function Heat({ filters }) {
  const { data, error, loading, reload } = useApi(() => api.heatmap(filters), [JSON.stringify(filters)]);
  const cells = data?.cells ?? [];
  const max = Math.max(1, ...cells.map((c) => c.crimes));
  const grid = {};
  cells.forEach((c) => {
    grid[`${c.day_of_week}-${c.hour}`] = c.crimes;
  });
  return (
    <Case title="When it happens: hour by weekday" tag="Heatmap">
      {error && <ErrorBox message={error} onRetry={reload} />}
      {loading && !data && <Spinner />}
      {data && (
        <>
          <div className={`heat ${loading ? "dim" : ""}`} role="img" aria-label="Crime counts by hour and weekday">
            <div />
            {Array.from({ length: 24 }, (_, h) => (
              <div key={h} className="heat-h">{h}</div>
            ))}
            {DAYS.map((d, di) => (
              <Fragment key={d}>
                <div className="heat-d">{d}</div>
                {Array.from({ length: 24 }, (_, h) => {
                  const v = grid[`${di}-${h}`] || 0;
                  return (
                    <div
                      key={h}
                      className="heat-c"
                      style={{ background: `rgba(200,32,47,${0.08 + 0.92 * (v / max)})` }}
                      title={`${d} at ${h}:00, ${fmt(v)} crimes`}
                    />
                  );
                })}
              </Fragment>
            ))}
          </div>
          <p className="hint">Darker means more crimes. Hours 0 and 12 are inflated by default timestamps.</p>
        </>
      )}
    </Case>
  );
}

export default function Dashboard() {
  const meta = useMeta();
  const [filters, setFilters] = useState(EMPTY);
  const params = useMemo(() => toParams(filters), [filters]);
  const slice = useApi(() => api.slice(params), [JSON.stringify(params)]);
  const set = (k) => (e) => setFilters({ ...filters, [k]: e.target.value });
  const d = slice.data;
  const top = d?.by_crime_type?.[0];

  return (
    <div className="container pad">
      <h1>Dashboard</h1>
      <p className="lead">
        Filter the records, then roll up and drill down. Every number below comes from the warehouse.
      </p>

      <Case title="Filters" tag="Narrow the search" className="filters-case">
        <div className="filters">
          <Field label="Year">
            <select value={filters.year} onChange={set("year")}>
              <option value="">All years</option>
              {meta.years.map((y) => (<option key={y} value={y}>{y}</option>))}
            </select>
          </Field>
          <Field label="Month">
            <select value={filters.month} onChange={set("month")}>
              <option value="">All months</option>
              {meta.months.map((m) => (<option key={m} value={m}>{MONTHS[m - 1]}</option>))}
            </select>
          </Field>
          <Field label="Police district">
            <select value={filters.district} onChange={set("district")}>
              <option value="">All districts</option>
              {meta.districts.map((x) => (<option key={x} value={x}>District {x}</option>))}
            </select>
          </Field>
          <Field label="Crime type">
            <select value={filters.crime_type} onChange={set("crime_type")}>
              <option value="">All crime types</option>
              {meta.crime_types.map((c) => (<option key={c} value={c}>{title(c)}</option>))}
            </select>
          </Field>
          <Field label="Season">
            <select value={filters.season} onChange={set("season")}>
              <option value="">All seasons</option>
              {meta.seasons.map((s) => (<option key={s} value={s}>{title(s)}</option>))}
            </select>
          </Field>
          <button className="btn ghost" onClick={() => setFilters(EMPTY)}>Clear filters</button>
        </div>
      </Case>

      {slice.error && <ErrorBox message={slice.error} onRetry={slice.reload} />}
      <div className={`stat-row ${slice.loading ? "dim" : ""}`}>
        <Stat value={d ? fmt(d.total_crimes) : "..."} label="Crimes matching the filters" />
        <Stat value={d ? fmt(d.total_arrests) : "..."} label="Arrests" tone="amber" />
        <Stat value={d ? `${d.arrest_rate_pct}%` : "..."} label="Arrest rate" />
        <Stat value={top ? title(top.crime_type) : "..."} label="Most common crime" note={top ? `${fmt(top.crimes)} reports` : ""} tone="red" />
      </div>

      <DrillChart filters={params} />
      <Tape />
      <div className="grid-2">
        <TopAreas filters={params} />
        <Case title="Crime types in this selection" tag="Result table">
          {d && (
            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr><th>Crime type</th><th>Crimes</th><th>Arrests</th><th>Arrest rate</th></tr>
                </thead>
                <tbody>
                  {d.by_crime_type.map((r) => (
                    <tr key={r.crime_type}>
                      <td>{title(r.crime_type)}</td>
                      <td className="num">{fmt(r.crimes)}</td>
                      <td className="num">{fmt(r.arrests)}</td>
                      <td className="num">{r.arrest_rate_pct}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {!d && !slice.error && <Spinner />}
        </Case>
      </div>
      <Heat filters={params} />
    </div>
  );
}
