import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api.js";
import { useApi } from "../useApi.js";
import { useMeta } from "../MetaContext.jsx";
import { Case, Disclaimer, ErrorBox, Field, Spinner, Stat } from "../components/Ui.jsx";

const TICK = { fill: "#9a97a3", fontSize: 12 };
const TIP = { background: "#141418", border: "1px solid #3a3a44", color: "#e7e2d6" };

export default function Forecast() {
  const meta = useMeta();
  const [area, setArea] = useState("26");
  const [days, setDays] = useState(7);
  const { data, error, loading, reload } = useApi(
    () => api.forecast({ community_area: Number(area), days }),
    [area, days]
  );

  const chart = useMemo(() => {
    if (!data) return [];
    const rows = data.recent_actuals.map((r) => ({ date: r.date, actual: r.crimes, expected: null }));
    rows[rows.length - 1].expected = rows[rows.length - 1].actual;
    data.forecast.forEach((f) => rows.push({ date: f.date, actual: null, expected: f.predicted_crimes }));
    return rows;
  }, [data]);

  return (
    <div className="container pad">
      <h1>Forecast</h1>
      <p className="lead">
        Pick a community area and how many days ahead. The model starts from the last day in the
        data and uses its own earlier estimates for the later days.
      </p>
      <Disclaimer />
      <Case title="Choose an area" tag="Forecast inputs">
        <div className="filters">
          <Field label="Community area">
            <select value={area} onChange={(e) => setArea(e.target.value)}>
              {meta.community_areas.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </Field>
          <Field label="Days ahead">
            <div className="seg" role="group" aria-label="Days ahead">
              {[1, 2, 3, 4, 5, 6, 7].map((n) => (
                <button key={n} className={days === n ? "on" : ""} onClick={() => setDays(n)}>{n}</button>
              ))}
            </div>
          </Field>
        </div>
      </Case>

      {error && <ErrorBox message={error} onRetry={reload} />}
      {loading && !data && <Spinner label="Running the forecast..." />}
      {data && (
        <>
          <div className={`stat-row ${loading ? "dim" : ""}`}>
            <Stat value={data.forecast[0].predicted_crimes} label={`Expected crimes on ${data.forecast[0].date}`} note={data.area_name} tone="amber" />
            <Stat value={`\u00b1 ${data.model_mae_all_areas}`} label="Typical error per area per day" note="Measured on 2025 to 2026 test data" />
            <Stat value={data.data_as_of} label="Last day in the data" note="Forecast days start after this date" tone="red" />
          </div>
          <Case title={`${data.area_name}: last 30 days and the days ahead`} tag="Actual vs expected">
            <div className={loading ? "dim" : ""}>
              <ResponsiveContainer width="100%" height={340}>
                <LineChart data={chart} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
                  <CartesianGrid stroke="#26262c" vertical={false} />
                  <XAxis dataKey="date" tick={TICK} tickFormatter={(v) => v.slice(5)} interval={3} />
                  <YAxis tick={TICK} width={40} allowDecimals={false} />
                  <Tooltip contentStyle={TIP} />
                  <Legend />
                  <ReferenceLine x={data.data_as_of} stroke="#ffd21f" strokeDasharray="4 4" label={{ value: "Data ends", fill: "#ffd21f", fontSize: 12, position: "insideTopLeft" }} />
                  <Line type="monotone" dataKey="actual" name="Recorded" stroke="#f2a33a" strokeWidth={2} dot={false} connectNulls />
                  <Line type="monotone" dataKey="expected" name="Expected" stroke="#e5383b" strokeWidth={2.5} strokeDasharray="6 4" dot={{ r: 3 }} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="hint">{data.note}</p>
            <div className="table-scroll">
              <table className="table">
                <thead><tr><th>Date</th><th>Expected crimes</th></tr></thead>
                <tbody>
                  {data.forecast.map((f) => (
                    <tr key={f.date}><td>{f.date}</td><td className="num">{f.predicted_crimes}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Case>
        </>
      )}
    </div>
  );
}
