import { useState } from "react";
import { api } from "../api.js";
import { useMeta } from "../MetaContext.jsx";
import { Case, Disclaimer, ErrorBox, Field, Spinner, Stat, title } from "../components/Ui.jsx";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const hourLabel = (h) => `${h % 12 === 0 ? 12 : h % 12} ${h < 12 ? "am" : "pm"}`;

// Overall importance of each input in the trained tree (from ml/results/tree_feature_importance.csv).
const FACTORS = [
  { name: "Domestic incident", value: 81.6 },
  { name: "Location type", value: 11.9 },
  { name: "Hour of the day", value: 3.2 },
  { name: "Police district", value: 2.7 },
  { name: "Community area", value: 0.5 },
  { name: "Day of the week", value: 0.2 },
  { name: "Season", value: 0.0 },
];

const START = {
  hour: 22,
  day_of_week: 5,
  season: "SUMMER",
  location_group: "STREET",
  community_area: 25,
  district: 15,
  domestic: false,
};

export default function Violence() {
  const meta = useMeta();
  const [form, setForm] = useState(START);
  const [state, setState] = useState({ loading: false, error: null, result: null });
  const set = (k, num) => (e) =>
    setForm({ ...form, [k]: num ? Number(e.target.value) : e.target.value });

  async function run(e) {
    e.preventDefault();
    setState({ loading: true, error: null, result: null });
    try {
      setState({ loading: false, error: null, result: await api.violence(form) });
    } catch (err) {
      setState({ loading: false, error: err.message, result: null });
    }
  }

  const r = state.result;
  const pct = r ? Math.round(r.probability_violent * 1000) / 10 : 0;

  return (
    <div className="container pad">
      <h1>Violence risk</h1>
      <p className="lead">
        Describe an incident by when and where it happened. A decision tree estimates how likely it
        is to be a violent crime.
      </p>
      <Disclaimer />
      <div className="split split-even">
        <Case title="Describe the incident" tag="Inputs">
          <form onSubmit={run} className="form">
            <Field label="Hour of the day">
              <select value={form.hour} onChange={set("hour", true)}>
                {Array.from({ length: 24 }, (_, h) => (<option key={h} value={h}>{hourLabel(h)}</option>))}
              </select>
            </Field>
            <Field label="Day of the week">
              <select value={form.day_of_week} onChange={set("day_of_week", true)}>
                {DAYS.map((d, i) => (<option key={d} value={i}>{d}</option>))}
              </select>
            </Field>
            <Field label="Season">
              <select value={form.season} onChange={set("season")}>
                {meta.seasons.map((s) => (<option key={s} value={s}>{title(s)}</option>))}
              </select>
            </Field>
            <Field label="Location type">
              <select value={form.location_group} onChange={set("location_group")}>
                {meta.location_groups.map((s) => (<option key={s} value={s}>{title(s)}</option>))}
              </select>
            </Field>
            <Field label="Community area">
              <select value={form.community_area} onChange={set("community_area", true)}>
                {meta.community_areas.map((a) => (<option key={a.id} value={a.id}>{a.name}</option>))}
              </select>
            </Field>
            <Field label="Police district">
              <select value={form.district} onChange={set("district", true)}>
                {meta.districts.map((d) => (<option key={d} value={d}>District {d}</option>))}
              </select>
            </Field>
            <label className="check wide">
              <input type="checkbox" checked={form.domestic} onChange={(e) => setForm({ ...form, domestic: e.target.checked })} />
              The report was flagged as a domestic incident
            </label>
            <button className="btn primary wide" type="submit" disabled={state.loading}>
              {state.loading ? "Assessing..." : "Assess this incident"}
            </button>
          </form>
        </Case>

        <div className="side">
          {state.loading && <Spinner label="Reading the tree..." />}
          {state.error && <ErrorBox message={state.error} />}
          {!r && !state.loading && !state.error && (
            <Case title="Result" tag="Waiting">
              <p className="hint">Fill in the form and choose "Assess this incident". The result appears here.</p>
            </Case>
          )}
          {r && (
            <Case title="Result" tag={r.prediction}>
              <p className={`verdict ${r.prediction === "violent" ? "red" : "ok"}`}>
                {r.prediction === "violent" ? "Likely violent" : "Likely not violent"}
              </p>
              <p className="result-big">{pct}% chance of a violent crime</p>
              <div className="gauge" aria-hidden="true">
                <div className="gauge-fill" style={{ width: `${pct}%` }} />
                <div className="gauge-avg" style={{ left: `${r.average_violent_share_pct}%` }}>
                  <span>average {r.average_violent_share_pct}%</span>
                </div>
              </div>
              <p className="hint">
                That is {r.relative_to_average} times the average share of violent crimes in the data.
                The label switches to "violent" at {Math.round(r.threshold * 100)}%.
              </p>
              <div className="stat-row compact">
                <Stat value={`${r.model_accuracy_pct}%`} label="Model accuracy" />
                <Stat value={`${r.model_precision_violent_pct}%`} label="Violent calls that were right" />
                <Stat value={`${r.model_recall_violent_pct}%`} label="Violent crimes it catches" tone="red" />
              </div>
              <p className="hint">{r.note}</p>
            </Case>
          )}
          <Case title="What the tree relies on" tag="Main factors">
            <ul className="bars">
              {FACTORS.map((f) => (
                <li key={f.name}>
                  <span>{f.name}</span>
                  <span className="bar"><i style={{ width: `${f.value}%` }} /></span>
                  <span className="num">{f.value.toFixed(1)}%</span>
                </li>
              ))}
            </ul>
            <p className="hint">Share of the tree's decisions that depend on each input, across all incidents.</p>
          </Case>
        </div>
      </div>
    </div>
  );
}
