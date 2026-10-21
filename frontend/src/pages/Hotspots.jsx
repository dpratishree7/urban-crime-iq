import { useState } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMapEvents } from "react-leaflet";
import { api } from "../api.js";
import { useApi } from "../useApi.js";
import { useMeta } from "../MetaContext.jsx";
import { Case, Disclaimer, ErrorBox, Field, Spinner, fmt, title } from "../components/Ui.jsx";

const RISK = { High: "#e5383b", Medium: "#f2a33a", Low: "#5fa88c" };

function Picker({ onPick }) {
  useMapEvents({
    click(e) {
      onPick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

export default function Hotspots() {
  const meta = useMeta();
  const hs = useApi(api.hotspots, []);
  const [area, setArea] = useState("");
  const [pick, setPick] = useState({ loading: false, error: null, result: null });

  async function lookup(body) {
    setPick({ loading: true, error: null, result: null });
    try {
      setPick({ loading: false, error: null, result: await api.lookup(body) });
    } catch (e) {
      setPick({ loading: false, error: e.message, result: null });
    }
  }
  const byMap = (lat, lon) => {
    setArea("");
    lookup({ latitude: lat, longitude: lon });
  };
  const byArea = (e) => {
    setArea(e.target.value);
    if (e.target.value) lookup({ community_area: Number(e.target.value) });
  };

  const clusters = hs.data?.clusters ?? [];
  const biggest = Math.max(1, ...clusters.map((c) => c.sample_size));
  const r = pick.result;

  return (
    <div className="container pad">
      <h1>Hotspots</h1>
      <p className="lead">
        K-Means groups crime locations into eight zones. Click the map or choose a community area to
        see which zone it falls in.
      </p>
      <Disclaimer />
      {hs.error && <ErrorBox message={hs.error} onRetry={hs.reload} />}
      {hs.loading && !hs.data && <Spinner label="Plotting the clusters..." />}
      {hs.data && (
        <div className="split">
          <Case title="Crime zones" tag="Click to look up a point" className="map-case">
            <div className="map-wrap">
              <MapContainer center={[41.835, -87.7]} zoom={10} scrollWheelZoom>
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  maxZoom={19}
                />
                <Picker onPick={byMap} />
                {clusters.map((c) => (
                  <CircleMarker
                    key={c.cluster}
                    center={[c.centre_lat, c.centre_lon]}
                    radius={12 + 22 * Math.sqrt(c.sample_size / biggest)}
                    pathOptions={{
                      color: RISK[c.risk_level],
                      fillColor: RISK[c.risk_level],
                      fillOpacity: 0.28,
                      weight: 2,
                    }}
                  >
                    <Tooltip>
                      Zone {c.cluster}: {c.risk_level} volume, mostly {title(c.top_crime_type).toLowerCase()}
                    </Tooltip>
                  </CircleMarker>
                ))}
                {r && (
                  <CircleMarker
                    center={[r.latitude, r.longitude]}
                    radius={7}
                    pathOptions={{ color: "#ffd21f", fillColor: "#ffd21f", fillOpacity: 1, weight: 2 }}
                  />
                )}
              </MapContainer>
            </div>
            <div className="legend">
              {Object.entries(RISK).map(([k, v]) => (
                <span key={k}><i style={{ background: v }} /> {k} volume</span>
              ))}
              <span>Circle size shows how many crimes fall in the zone.</span>
            </div>
          </Case>

          <div className="side">
            <Case title="Look up a place" tag="Zone finder">
              <Field label="Community area">
                <select value={area} onChange={byArea}>
                  <option value="">Choose an area, or click the map</option>
                  {meta.community_areas.map((a) => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
              </Field>
              {pick.loading && <Spinner label="Finding the zone..." />}
              {pick.error && <ErrorBox message={pick.error} />}
              {r && (
                <div className="result">
                  <p className="result-kicker">{r.area_name ? r.area_name : "Selected point"}</p>
                  <p className="result-big">
                    Zone {r.cluster} <span className={`badge ${r.risk_level.toLowerCase()}`}>{r.risk_level} volume</span>
                  </p>
                  <dl className="facts">
                    <dt>Most common crime in this zone</dt>
                    <dd>{title(r.top_crime_type)}</dd>
                    <dt>Distance to the zone centre</dt>
                    <dd>{r.distance_to_centre_km} km</dd>
                  </dl>
                  <p className="hint">{r.note}</p>
                </div>
              )}
            </Case>

            <Case title="All eight zones" tag="From the model">
              <div className="table-scroll">
                <table className="table">
                  <thead>
                    <tr><th>Zone</th><th>Volume</th><th>Top crime</th><th>Share</th></tr>
                  </thead>
                  <tbody>
                    {clusters.map((c) => (
                      <tr key={c.cluster}>
                        <td>{c.cluster}</td>
                        <td><span className={`badge ${c.risk_level.toLowerCase()}`}>{c.risk_level}</span></td>
                        <td>{title(c.top_crime_type)}</td>
                        <td className="num">{c.share_pct}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="hint">
                {hs.data.note} Volume tiers compare recorded incident counts. They are not adjusted for
                population. Based on a sample of {fmt(hs.data.sample_total)} crimes.
              </p>
            </Case>
          </div>
        </div>
      )}
    </div>
  );
}
