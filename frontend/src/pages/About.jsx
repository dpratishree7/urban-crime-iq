import { Case, Tape } from "../components/Ui.jsx";

// Edit this list with your team's names and roles.
const TEAM = [
  { name: "Team member 1", role: "Data warehouse, API and backend" },
  { name: "Team member 2", role: "Machine learning models and evaluation" },
];

export default function About() {
  return (
    <div className="container pad">
      <h1>About this project</h1>
      <p className="lead">
        An end-to-end data warehousing and data mining project on Chicago's police-reported crime
        records from January 2023 to September 2026.
      </p>

      <div className="grid-2">
        <Case title="The data" tag="Source">
          <p>
            About 921,000 reported incidents from the City of Chicago Data Portal, cleaned and
            combined with neighbourhood indicators (poverty, unemployment, per capita income and
            population by community area), daily weather and public holidays.
          </p>
          <p className="hint">
            Neighbourhood indicators date from 2008 to 2012 and population from the 2020 Census, so
            they may not match 2023 to 2026 exactly.
          </p>
        </Case>
        <Case title="How it fits together" tag="Method">
          <p>
            Raw data is audited, cleaned and enriched in Python, then loaded into a PostgreSQL star
            schema. A FastAPI service exposes the warehouse and four models, and this React site
            calls it. Nothing on the site is hard-coded.
          </p>
        </Case>
      </div>

      <Case title="How each model did" tag="Compared with a baseline">
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr><th>Model</th><th>Result</th><th>Compared with</th></tr>
            </thead>
            <tbody>
              <tr><td>K-Means hotspots</td><td>8 zones, silhouette 0.41</td><td>K from 5 to 15</td></tr>
              <tr><td>Regression forecast</td><td>Error 2.42 crimes per area per day, R&sup2; 0.80</td><td>Same as last week: 3.31, R&sup2; 0.63</td></tr>
              <tr><td>Decision tree</td><td>73.2% accuracy, finds 40% of violent crimes</td><td>Always "not violent": 66.4%</td></tr>
              <tr><td>Apriori patterns</td><td>34 rules, lift up to 3.06</td><td>Descriptive, no baseline</td></tr>
            </tbody>
          </table>
        </div>
      </Case>
      <Tape />

      <div className="grid-2">
        <Case title="Limits you should know" tag="Limitations">
          <ul className="plain">
            <li>These are reported crimes. Crimes that are not reported do not appear.</li>
            <li>About 6% of reports carry a default time (midnight or noon), so hour-of-day charts run high at hours 0 and 12.</li>
            <li>The forecast is a next-day estimate and gets less reliable further out. Weather uses monthly averages.</li>
            <li>The violence model catches only part of violent crime and leans mostly on the domestic flag.</li>
            <li>Patterns describe what occurs together, not what causes what.</li>
          </ul>
        </Case>
        <Case title="Ethics" tag="Responsible use">
          <ul className="plain">
            <li>No model uses race or ethnicity, and none predicts anything about an individual.</li>
            <li>Areas with more policing produce more reports, so counts can reflect where police look, not only where crime happens.</li>
            <li>This is a study project. It must not be used to decide policing or to judge neighbourhoods.</li>
          </ul>
        </Case>
      </div>

      <Case title="Team" tag="Who built this">
        <ul className="plain">
          {TEAM.map((m) => (
            <li key={m.name}><strong>{m.name}</strong>: {m.role}</li>
          ))}
        </ul>
      </Case>
    </div>
  );
}
