import { useEffect, useState } from "react";
import "./App.css";
import { ComposedChart, Line, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [wetter, setWetter] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/weather/today`)
      .then((antwort) => antwort.json())
      .then((daten) => setWetter(daten));
  }, []);

  if (wetter === null) {
    return <p className="app">Lade Wetterdaten …</p>;
  }

  return (
    <main className="app">
      <h1>🚆 Pendler</h1>
      <h2>{wetter.city}</h2>

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
    </main>
  );
}

export default App;