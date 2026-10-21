import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useApi } from "../useApi.js";
import Skyline from "../components/Skyline.jsx";
import { ErrorBox, Spinner, Stat, Tape, fmt, title } from "../components/Ui.jsx";

const TAPE_TEXT = "CRIME SCENE   DO NOT CROSS   ".repeat(16);

export default function Home() {
  const { data, error, loading, reload } = useApi(api.summary, []);

  return (
    <>
      <section className="hero">
        <div className="hero-tape" aria-hidden="true">
          <span>{TAPE_TEXT}</span>
        </div>
        <div className="container hero-inner">
          <p className="stamp stamp-lg">Case file: Chicago, 2023 to 2026</p>
          <h1>Chicago's reported crimes, read the way an analyst would.</h1>
          <p className="hero-sub">
            A data warehouse, four mining models and a live API, built on the city's open police
            records. Ask where, when and what kind, then see what the models make of it.
          </p>
          <div className="hero-actions">
            <Link to="/dashboard" className="btn primary">
              Open the dashboard
            </Link>
            <Link to="/predict/hotspots" className="btn ghost">
              Try the predictions
            </Link>
          </div>
        </div>
        <Skyline />
      </section>

      <div className="container pad">
        {error && <ErrorBox message={error} onRetry={reload} />}
        {loading && !data && <Spinner label="Counting the reports..." />}
        {data && (
          <div className="stat-row">
            <Stat
              value={fmt(data.total_crimes)}
              label="Crimes on record"
              note={`${data.date_from} to ${data.date_to}`}
            />
            <Stat
              value={title(data.top_crime_type)}
              label="Most common crime"
              note={`${fmt(data.top_crime_type_count)} reports`}
              tone="amber"
            />
            <Stat
              value={`${data.arrest_rate_pct}%`}
              label="Of reports ended in an arrest"
              note="Across every crime type"
            />
            <Stat
              value={`${data.violent_share_pct}%`}
              label="Of reports were violent crimes"
              note="Battery, assault, robbery, homicide and similar"
              tone="red"
            />
          </div>
        )}
      </div>

      <Tape />

      <div className="container pad">
        <h2>What is inside the file</h2>
        <div className="notes">
          <div>
            <h3>A warehouse you can slice</h3>
            <p>
              The reports are loaded into a star schema in PostgreSQL. The dashboard rolls them up
              by year, month, day and hour, and drills down from the city to a single beat.
            </p>
          </div>
          <div>
            <h3>Four models, each with a baseline</h3>
            <p>
              K-Means groups crime locations, a regression forecasts daily counts, a decision tree
              screens for violence, and Apriori finds patterns that go together. Each is compared
              with a simple baseline.
            </p>
          </div>
          <div>
            <h3>Honest about its limits</h3>
            <p>
              The numbers describe reported crime, not all crime. Every prediction page says what
              the model can and cannot tell you.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
