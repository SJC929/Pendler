import { useEffect, useState } from "react";
import "./App.css";
import { ComposedChart, Line, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";
import Zuege from "./Zuege";
import StationPrognose from "./StationPrognose";
import PendelRegen from "./PendelRegen";
import Verkehr from "./Verkehr";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const STANDARD_ORT = { name: "Basel", canton: "Basel-Stadt", lat: 47.56, lon: 7.59 };

// Wettercode → Symbol
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

// "2026-10-28" → "Mi."
function wochentag(datum) {
  return new Date(datum).toLocaleDateString("de-CH", { weekday: "short" });
}

// "2026-12-25" → "Fr., 25. Dezember"
function datumSchoen(datum) {
  return new Date(datum).toLocaleDateString("de-CH", {
    weekday: "short",
    day: "numeric",
    month: "long",
  });
}

// Gleicher Ort? (Name + Kanton vergleichen)
function gleich(a, b) {
  return a.name === b.name && a.canton === b.canton;
}

// Gepinnte Orte aus dem Browser laden
function ladePins() {
  try {
    const gespeichert = localStorage.getItem("pendler-pins");
    const pins = gespeichert ? JSON.parse(gespeichert) : [];
    return pins.length > 0 ? pins : [STANDARD_ORT];
  } catch {
    return [STANDARD_ORT];
  }
}

// Zuletzt geöffneten Tab laden
function ladeBereich() {
  try {
    return localStorage.getItem("pendler-bereich") || "wetter";
  } catch {
    return "wetter";
  }
}

function App() {
  // 📝 Gedächtnis
  const [bereich, setBereich] = useState(ladeBereich); // «wetter», «zuege» oder «prognose»
  const [pins, setPins] = useState(ladePins);
  const [ort, setOrt] = useState(() => ladePins()[0]);
  const [suche, setSuche] = useState("");
  const [vorschlaege, setVorschlaege] = useState([]);
  const [wetter, setWetter] = useState(null);
  const [woche, setWoche] = useState(null);
  const [pollen, setPollen] = useState(null);
  const [feiertag, setFeiertag] = useState(null);
  const [ansicht, setAnsicht] = useState("heute");
  const [istHandy, setIstHandy] = useState(window.innerWidth < 500);

  // 🔔 Bildschirmbreite beobachten
  useEffect(() => {
    const pruefen = () => setIstHandy(window.innerWidth < 500);
    window.addEventListener("resize", pruefen);
    return () => window.removeEventListener("resize", pruefen);
  }, []);

  // 🔔 Gewählten Tab merken
  useEffect(() => {
    try {
      localStorage.setItem("pendler-bereich", bereich);
    } catch {
      // Speichern nicht möglich → ignorieren
    }
  }, [bereich]);

  // 🔔 Pins im Browser speichern, sobald sie sich ändern
  useEffect(() => {
    try {
      localStorage.setItem("pendler-pins", JSON.stringify(pins));
    } catch {
      // Speichern nicht möglich (z. B. privater Modus) → ignorieren
    }
  }, [pins]);

  // 🔔 Alle Daten holen, sobald sich der Ort ändert
  useEffect(() => {
    const parameter = `lat=${ort.lat}&lon=${ort.lon}&city=${encodeURIComponent(ort.name)}`;
    setWetter(null);
    setWoche(null);
    setPollen(null);
    setFeiertag(null);

    fetch(`${API_URL}/weather/today?${parameter}`)
      .then((antwort) => antwort.json())
      .then((daten) => setWetter(daten));

    fetch(`${API_URL}/weather/week?${parameter}`)
      .then((antwort) => antwort.json())
      .then((daten) => setWoche(daten));

    fetch(`${API_URL}/pollen?lat=${ort.lat}&lon=${ort.lon}`)
      .then((antwort) => antwort.json())
      .then((daten) => setPollen(daten));

    fetch(`${API_URL}/holidays/next?canton=${encodeURIComponent(ort.canton)}`)
      .then((antwort) => antwort.json())
      .then((daten) => setFeiertag(daten));
  }, [ort]);

  // 🔔 Orte suchen, während der Nutzer tippt (kurz warten, dann suchen)
  useEffect(() => {
    if (suche.length < 2) {
      setVorschlaege([]);
      return;
    }
    const timer = setTimeout(() => {
      fetch(`${API_URL}/locations/search?q=${encodeURIComponent(suche)}`)
        .then((antwort) => antwort.json())
        .then((daten) => setVorschlaege(daten));
    }, 300);
    return () => clearTimeout(timer);
  }, [suche]);

  // Ort auswählen → anzeigen und pinnen
  function waehleOrt(neuerOrt) {
    setOrt(neuerOrt);
    setSuche("");
    setVorschlaege([]);
    if (!pins.some((p) => gleich(p, neuerOrt))) {
      setPins([...pins, neuerOrt]);
    }
  }

  // Pin entfernen
  function entfernePin(pin) {
    const rest = pins.filter((p) => !gleich(p, pin));
    if (rest.length === 0) return; // mindestens ein Ort bleibt
    setPins(rest);
    if (gleich(pin, ort)) setOrt(rest[0]);
  }

  // Text für den Feiertag
  function feiertagTitel(tage) {
    if (tage === 0) return "Heute Feiertag";
    if (tage === 1) return "Morgen Feiertag";
    return "Nächster Feiertag";
  }

  // 🖥️ Die Seite
  return (
    <main className="app">
      <h1>🚆 Pendler</h1>

      {/* 🧭 Navigation */}
      <nav className="nav">
        <button className={bereich === "wetter" ? "aktiv" : ""} onClick={() => setBereich("wetter")}>
          🌦️ Wetter
        </button>
        <button className={bereich === "zuege" ? "aktiv" : ""} onClick={() => setBereich("zuege")}>
          🚆 Verbindungen
        </button>
        <button className={bereich === "prognose" ? "aktiv" : ""} onClick={() => setBereich("prognose")}>
          🔮 Prognose
        </button>
        <button className={bereich === "verkehr" ? "aktiv" : ""} onClick={() => setBereich("verkehr")}>
          🚗 Verkehr
        </button>
      </nav>

      {/* ===== Bereich: Wetter ===== */}
      <div className="bereich" hidden={bereich !== "wetter"}>
        {/* Suchfeld */}
        <div className="suche">
          <input
            type="text"
            placeholder="🔍 Ort suchen, z. B. Winterthur"
            value={suche}
            onChange={(e) => setSuche(e.target.value)}
          />
          {vorschlaege.length > 0 && (
            <ul className="vorschlaege">
              {vorschlaege.map((v) => (
                <li key={`${v.name}-${v.lat}-${v.lon}`} onClick={() => waehleOrt(v)}>
                  📍 {v.name} <span className="kanton">{v.canton}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Gepinnte Orte */}
        <div className="pins">
          {pins.map((pin) => (
            <span
              key={`${pin.name}-${pin.lat}-${pin.lon}`}
              className={gleich(pin, ort) ? "pin aktiv" : "pin"}
              onClick={() => setOrt(pin)}
            >
              📌 {pin.name}
              <button
                className="pin-x"
                onClick={(e) => {
                  e.stopPropagation();
                  entfernePin(pin);
                }}
              >
                ✕
              </button>
            </span>
          ))}
        </div>

        <h2>
          {ort.name} <span className="kanton">{ort.canton}</span>
        </h2>

        {/* Feiertag */}
        {feiertag && feiertag.name && (
          <div className={feiertag.days_until <= 1 ? "feiertag bald" : "feiertag"}>
            📅 {feiertagTitel(feiertag.days_until)} in {feiertag.canton}:{" "}
            <strong>{datumSchoen(feiertag.date)}</strong> · {feiertag.name}
          </div>
        )}

        {/* Regenwarnung für die Pendelzeiten */}
        <PendelRegen pins={pins} ort={ort} />

        {/* Umschalter */}
        <div className="umschalter">
          <button className={ansicht === "heute" ? "aktiv" : ""} onClick={() => setAnsicht("heute")}>
            Heute
          </button>
          <button className={ansicht === "woche" ? "aktiv" : ""} onClick={() => setAnsicht("woche")}>
            7 Tage
          </button>
        </div>

        {/* ⏳ Laden */}
        {(wetter === null || woche === null) && <p>Lade Wetterdaten …</p>}

        {/* Ansicht: Heute */}
        {wetter !== null && ansicht === "heute" && (
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
              <div className={`karte pollen-${pollen ? pollen.key : "none"}`}>
                <p className="label">🌸 Pollen</p>
                <p className="wert">{pollen ? pollen.level : "…"}</p>
                <p className="label">
                  {pollen && pollen.type ? pollen.type : "heute keine Belastung"}
                </p>
              </div>
            </div>

            <h3>Verlauf heute</h3>
            <ResponsiveContainer width="100%" height={250}>
              <ComposedChart data={wetter.hourly} margin={{ top: 5, right: 0, left: -10, bottom: 0 }}>
                <XAxis
                  dataKey="time"
                  ticks={istHandy ? ["00:00", "12:00", "15:00", "18:00"] : undefined}
                  interval={istHandy ? 0 : 3}
                  tick={{ fontSize: 12 }}
                />
                <YAxis yAxisId="temp" unit="°" width={40} tick={{ fontSize: 12 }} />
                <YAxis yAxisId="regen" orientation="right" unit="%" domain={[0, 100]} width={40} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar yAxisId="regen" dataKey="rain_probability" name="Regen" fill="#85B7EB" />
                <Line yAxisId="temp" dataKey="temperature" name="Temperatur" stroke="#D85A30" strokeWidth={3} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </>
        )}

        {/* Ansicht: 7 Tage */}
        {woche !== null && ansicht === "woche" && (
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
      </div>

      {/* ===== Bereich: Verbindungen ===== */}
      <div className="bereich" hidden={bereich !== "zuege"}>
        <Zuege />
      </div>

      {/* ===== Bereich: Prognose ===== */}
      <div className="bereich" hidden={bereich !== "prognose"}>
        <StationPrognose />
      </div>

    {/* ===== Bereich: Verkehr ===== */}
      <div className="bereich" hidden={bereich !== "verkehr"}>
        <Verkehr pins={pins} />
      </div>
      
    </main>
    
  );
        
}

export default App;