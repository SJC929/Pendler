import { useEffect, useState } from "react";
import "./App.css";

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
      <ul className="verlauf">
        {wetter.hourly.map((stunde) => (
          <li key={stunde.time}>
            {stunde.time} · {stunde.temperature}° · Regen {stunde.rain_probability} %
          </li>
        ))}
      </ul>
    </main>
  );
}

export default App;