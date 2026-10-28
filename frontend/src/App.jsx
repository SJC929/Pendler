import { useEffect, useState } from "react";
import "./App.css";
import { ComposedChart, Line, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// NEU: Wettercode → Symbol
function wetterSymbol(code) {
  if (code === 0) return "☀️";
  if (code <= 3) return "⛅";
  if (code <= 48) return "🌫️";
  if (code <= 67) return "🌧️";
  if (code <= 77) return "❄️";
  if (code <= 82) return "🌦️";
  if (code <= 86) return "🌨️";
  return "⛈️";
}

// NEU: "2026-10-28" → "Mi."
function wochentag(datum) {
  return new Date(datum).toLocaleDateString("de-CH", { weekday: "short" });
}

function App() {
  const [wetter, setWetter] = useState(null);
  const [woche, setWoche] = useState(null);         // NEU
  const [ansicht, setAnsicht] = useState("heute");  // NEU

  useEffect(() => {
    fetch(`${API_URL}/weather/today`)
      .then((antwort) => antwort.json())
      .then((daten) => setWetter(daten));

    // NEU: auch die Woche holen
    fetch(`${API_URL}/weather/week`)
      .then((antwort) => antwort.json())
      .then((daten) => setWoche(daten));
  }, []);

  if (wetter === null || woche === null) {
    return <p className="app">Lade Wetterdaten …</p>;
  }

  return (
    <main className="app">
      <h1>🚆 Pendler</h1>
      <h2>{wetter.city}</h2>

      {/* NEU: Umschalter */}
      <div className="umschalter">
        <button
          className={ansicht === "heute" ? "aktiv" : ""}
          onClick={() => setAnsicht("heute")}
        >
          Heute
        </button>
        <button
          className={ansicht === "woche" ? "aktiv" : ""}
          onClick={() => setAnsicht("woche")}
        >
          7 Tage
        </button>
      </div>

      {ansicht === "heute" && (
        <>
          <div className="karten">
            <div className="karte">
              <p className="label">Jetzt</p>
              <p className="wert">{wetter.now}°</p>
            </div>
            <div className="karte">
              <p className="label">Min / Max</p>
              <p className="wert">{wetter.min}° / {wetter.max}°</p>
            </div>
            <div className="karte">
              <p className="label">Schirm?</p>
              <p className="wert">{wetter.will_rain ? "☔ Ja" : "🌤️ Nein"}</p>
            </div>
          </div>

          <h3>Verlauf heute</h3>
          <ResponsiveContainer width="100%" height={250}>
            <ComposedChart data={wetter.hourly}>
              <XAxis dataKey="time" interval={3} />
              <YAxis yAxisId="temp" unit="°" />
              <YAxis yAxisId="regen" orientation="right" unit="%" domain={[0, 100]} />
              <Tooltip />
              <Legend />
              <Bar yAxisId="regen" dataKey="rain_probability" name="Regen" fill="#85B7EB" />
              <Line yAxisId="temp" dataKey="temperature" name="Temperatur" stroke="#D85A30" strokeWidth={3} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </>
      )}

      {/* NEU: 7-Tage-Kacheln */}
      {ansicht === "woche" && (
        <div className="woche">
          {woche.days.map((tag) => (
            <div className="tag" key={tag.date}>
              <p className="label">{wochentag(tag.date)}</p>
              <p className="symbol">{wetterSymbol(tag.weather_code)}</p>
              <p className="wert-klein">{tag.max}°</p>
              <p className="label">{tag.min}°</p>
              <p className="regen">💧 {tag.rain_probability} %</p>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}

export default App;