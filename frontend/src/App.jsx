import { Route, Routes } from "react-router-dom";
import { MetaProvider } from "./MetaContext.jsx";
import Navbar from "./components/Navbar.jsx";
import { Footer } from "./components/Ui.jsx";
import Home from "./pages/Home.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Hotspots from "./pages/Hotspots.jsx";
import Forecast from "./pages/Forecast.jsx";
import Violence from "./pages/Violence.jsx";
import Patterns from "./pages/Patterns.jsx";
import About from "./pages/About.jsx";

export default function App() {
  return (
    <div className="shell">
      <Navbar />
      <main>
        <MetaProvider>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/predict/hotspots" element={<Hotspots />} />
            <Route path="/predict/forecast" element={<Forecast />} />
            <Route path="/predict/violence" element={<Violence />} />
            <Route path="/predict/patterns" element={<Patterns />} />
            <Route path="/about" element={<About />} />
            <Route path="*" element={<div className="container pad"><h1>Page not found</h1></div>} />
          </Routes>
        </MetaProvider>
      </main>
      <Footer />
    </div>
  );
}
