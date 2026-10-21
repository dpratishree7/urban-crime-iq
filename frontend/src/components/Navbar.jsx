import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

const predict = [
  { to: "/predict/hotspots", label: "Hotspots" },
  { to: "/predict/forecast", label: "Forecast" },
  { to: "/predict/violence", label: "Violence risk" },
  { to: "/predict/patterns", label: "Patterns" },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const { pathname } = useLocation();

  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    const close = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const onPredict = pathname.startsWith("/predict");

  return (
    <header className="nav">
      <div className="container nav-row">
        <Link to="/" className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span>Crime Intelligence</span>
        </Link>
        <nav className="nav-links" aria-label="Main">
          <NavLink to="/" end>
            Home
          </NavLink>
          <NavLink to="/dashboard">Dashboard</NavLink>
          <div className="dropdown" ref={ref}>
            <button
              className={`dropdown-btn ${onPredict ? "active" : ""}`}
              aria-haspopup="true"
              aria-expanded={open}
              onClick={() => setOpen(!open)}
            >
              Predict <span aria-hidden="true">&#9662;</span>
            </button>
            {open && (
              <div className="dropdown-menu">
                {predict.map((p) => (
                  <NavLink key={p.to} to={p.to}>
                    {p.label}
                  </NavLink>
                ))}
              </div>
            )}
          </div>
          <NavLink to="/about">About</NavLink>
        </nav>
      </div>
      <div className="tape" />
    </header>
  );
}
