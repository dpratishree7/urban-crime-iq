export const fmt = (n) =>
  n === null || n === undefined || Number.isNaN(Number(n)) ? "-" : Number(n).toLocaleString("en-US");

export const title = (s) =>
  String(s || "").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());

export function Spinner({ label = "Pulling the records..." }) {
  return (
    <div className="spinner" role="status">
      <span className="spinner-ring" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorBox({ message, onRetry }) {
  return (
    <div className="errorbox" role="alert">
      <strong>This section could not load.</strong>
      <p>{message}</p>
      {onRetry && (
        <button className="btn ghost" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function Tape() {
  return <div className="tape" role="separator" />;
}

export function Case({ title: heading, tag, right, children, className = "" }) {
  return (
    <section className={`case ${className}`}>
      {(heading || tag || right) && (
        <header className="case-head">
          <div>{heading && <h3>{heading}</h3>}</div>
          <div className="case-head-right">
            {right}
            {tag && <span className="stamp">{tag}</span>}
          </div>
        </header>
      )}
      {children}
    </section>
  );
}

export function Stat({ value, label, note, tone = "" }) {
  return (
    <div className={`stat ${tone}`}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {note && <div className="stat-note">{note}</div>}
    </div>
  );
}

export function Field({ label, hint, children }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

export function Disclaimer() {
  return (
    <p className="disclaimer">
      <strong>Before you read the results.</strong> Statistical patterns from past reports, not a
      judgement about people or neighbourhoods.
    </p>
  );
}

export function Footer() {
  return (
    <footer className="footer">
      <div className="tape" />
      <div className="container footer-row">
        <p>
          Built for a data warehousing and data mining course. Records come from the City of Chicago
          Data Portal. This is a study project and must not be used for policing decisions.
        </p>
      </div>
    </footer>
  );
}
