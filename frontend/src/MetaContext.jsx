import { createContext, useContext } from "react";
import { api } from "./api.js";
import { useApi } from "./useApi.js";
import { ErrorBox, Spinner } from "./components/Ui.jsx";

const MetaCtx = createContext(null);
export const useMeta = () => useContext(MetaCtx);

// Loads /api/meta once. Every dropdown in the site is filled from it.
export function MetaProvider({ children }) {
  const { data, error, loading, reload } = useApi(api.meta, []);
  if (error)
    return (
      <div className="container pad">
        <ErrorBox message={error} onRetry={reload} />
      </div>
    );
  if (loading && !data)
    return (
      <div className="container pad">
        <Spinner label="Opening the case files..." />
      </div>
    );
  return <MetaCtx.Provider value={data}>{children}</MetaCtx.Provider>;
}
