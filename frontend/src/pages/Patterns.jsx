import { useRef, useState } from "react";
import { api } from "../api.js";
import { useApi } from "../useApi.js";
import { Case, Disclaimer, ErrorBox, Field, Spinner, title } from "../components/Ui.jsx";

const TIMES = ["MORNING", "AFTERNOON", "EVENING", "NIGHT"];
const PLACES = ["COMMERCIAL", "RESIDENTIAL", "STREET", "OTHER", "SCHOOL", "TRANSPORT"];
const SEASONS = ["WINTER", "SPRING", "SUMMER", "FALL"];
const EMPTY = { time_of_day: "", location_group: "", season: "", is_weekend: "", district: "" };

export default function Patterns() {
  const [f, setF] = useState(EMPTY);
  const districts = useRef([]);
  const { data, error, loading, reload } = useApi(() => api.patterns({ ...f, limit: 15 }), [JSON.stringify(f)]);
  if (data && data.districts_with_rules.length) districts.current = data.districts_with_rules;
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  return (
    <div className="container pad">
      <h1>Patterns</h1>
      <p className="lead">
        Association rules show which things tend to happen together. Choose conditions and the
        strongest matching patterns appear, ranked by lift.
      </p>
      <Disclaimer />
      <Case title="Conditions" tag="Pick any, or none">
        <div className="filters">
          <Field label="Time of day">
            <select value={f.time_of_day} onChange={set("time_of_day")}>
              <option value="">Any time</option>
              {TIMES.map((t) => (<option key={t} value={t}>{title(t)}</option>))}
            </select>
          </Field>
          <Field label="Location type">
            <select value={f.location_group} onChange={set("location_group")}>
              <option value="">Any location</option>
              {PLACES.map((t) => (<option key={t} value={t}>{title(t)}</option>))}
            </select>
          </Field>
          <Field label="Season">
            <select value={f.season} onChange={set("season")}>
              <option value="">Any season</option>
              {SEASONS.map((t) => (<option key={t} value={t}>{title(t)}</option>))}
            </select>
          </Field>
          <Field label="Weekday or weekend">
            <select value={f.is_weekend} onChange={set("is_weekend")}>
              <option value="">Any day</option>
              <option value="weekday">Weekday</option>
              <option value="weekend">Weekend</option>
            </select>
          </Field>
          <Field label="Police district" hint="Rules exist for a few districts only">
            <select value={f.district} onChange={set("district")}>
              <option value="">Any district</option>
              {districts.current.map((d) => (<option key={d} value={d}>District {Number(d.slice(1))}</option>))}
            </select>
          </Field>
          <button className="btn ghost" onClick={() => setF(EMPTY)}>Clear</button>
        </div>
      </Case>

      {error && <ErrorBox message={error} onRetry={reload} />}
      {loading && !data && <Spinner label="Searching the rules..." />}
      {data && (
        <Case title="Matching patterns" tag={`${data.matched} found`}>
          <p className={`hint ${loading ? "dim" : ""}`}>{data.message}</p>
          {data.rules.length > 0 && (
            <div className="table-scroll">
              <table className="table patterns">
                <thead>
                  <tr><th>Pattern</th><th>Support</th><th>Confidence</th><th>Lift</th></tr>
                </thead>
                <tbody>
                  {data.rules.map((r, i) => (
                    <tr key={i}>
                      <td>{r.meaning}</td>
                      <td className="num">{r.support_pct}%</td>
                      <td className="num">{r.confidence_pct}%</td>
                      <td className="num"><strong>{r.lift}</strong></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="hint">
            Support is how often the whole pattern appears. Confidence is how often the outcome
            follows the conditions. Lift compares that with the overall rate, so 2.0 means twice as often.
          </p>
          <p className="hint">{data.note}</p>
        </Case>
      )}
    </div>
  );
}
