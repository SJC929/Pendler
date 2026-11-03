import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// Pin → einfacher Ort {name, lat, lon}
const alsOrt = (p) => p && { name: p.name, lat: p.lat, lon: p.lon };

// 72 → "1 Std. 12 Min."
function dauerSchoen(min) {
  if (min < 60) return `${min} Min.`;
  const std = Math.floor(min / 60);
  const rest = min % 60;
  return rest ? `${std} Std. ${rest} Min.` : `${std} Std.`;
}

// Stau-Minuten → Farbe
function stufe(stauMin) {
  if (stauMin >= 15) return "hoch";
  if (stauMin >= 5) return "mittel";
  return "tief";
}

// Gespeicherte Adressen laden (alte Version hatte nur Pin-Namen → dann neu anfangen)
function ladeWahl() {
  try {
    const g = JSON.parse(localStorage.getItem("pendler-verkehr"));
    if (g && typeof g.von === "object" && typeof g.nach === "object") return g;
  } catch {
    // Laden nicht möglich → Standard
  }
  return { von: null, nach: null };
}

// 📍 Ein Adressfeld mit Vorschlägen
function AdressFeld({ label, wert, setWert, pins }) {
  const [offen, setOffen] = useState(false);
  const [text, setText] = useState("");
  const [vorschlaege, setVorschlaege] = useState([]);

  // 🔔 Suchen, während man tippt (ab 3 Zeichen, kurz warten)
  useEffect(() => {
    if (text.length < 3) {
      setVorschlaege([]);
      return;
    }
    const timer = setTimeout(() => {
      fetch(`${API_URL}/traffic/search?q=${encodeURIComponent(text)}`)
        .then((antwort) => (antwort.ok ? antwort.json() : []))
        .then((daten) => setVorschlaege(daten))
        .catch(() => setVorschlaege([]));
    }, 400);
    return () => clearTimeout(timer);
  }, [text]);

  function waehle(ort) {
    setWert(ort);
    setText("");
    setVorschlaege([]);
    setOffen(false);
  }

  return (
    <div className="adress-feld">
      <span className="label">{label}</span>

      {!offen ? (
        <button className="adress-wert" onClick={() => setOffen(true)}>
          <span>📍 {wert ? wert.name : "Adresse wählen"}</span>
          <span className="adress-stift">✎</span>
        </button>
      ) : (
        <>
          <div className="adress-eingabe">
            <input
              autoFocus
              type="text"
              placeholder="Adresse, z. B. Bahnhofstrasse 1, Zürich"
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === "Escape" && setOffen(false)}
            />
            <button onClick={() => setOffen(false)} aria-label="Schliessen">✕</button>
          </div>
          <ul className="adress-liste">
            {vorschlaege.map((v) => (
              <li key={`${v.name}-${v.lat}`} onClick={() => waehle(v)}>📍 {v.name}</li>
            ))}
            {pins.map((p) => (
              <li key={`pin-${p.name}-${p.lat}`} className="adress-pin" onClick={() => waehle(alsOrt(p))}>
                📌 {p.name}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export default function Verkehr({ pins }) {
  const [wahl, setWahl] = useState(ladeWahl);
  const [route, setRoute] = useState(null);
  const [fehler, setFehler] = useState("");
  const [stand, setStand] = useState(null);
  const [neuLaden, setNeuLaden] = useState(0);

  const von = wahl.von || alsOrt(pins[0]);
  const nach = wahl.nach || alsOrt(pins[1] || pins[0]);
  const gleicherOrt = von.lat === nach.lat && von.lon === nach.lon;

  // 🔔 Wahl merken
  useEffect(() => {
    try {
      localStorage.setItem("pendler-verkehr", JSON.stringify(wahl));
    } catch {
      // Speichern nicht möglich → ignorieren
    }
  }, [wahl]);

  // 🔔 Route holen
  useEffect(() => {
    if (gleicherOrt) return;
    setRoute(null);
    setFehler("");
    const parameter = new URLSearchParams({
      von_lat: von.lat, von_lon: von.lon, nach_lat: nach.lat, nach_lon: nach.lon,
    });
    fetch(`${API_URL}/traffic/route?${parameter}`)
      .then((antwort) => {
        if (!antwort.ok) throw new Error();
        return antwort.json();
      })
      .then((daten) => {
        setRoute(daten);
        setStand(new Date());
      })
      .catch(() => setFehler("Die Verkehrsdaten sind gerade nicht verfügbar. Bitte später nochmals versuchen."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [von.lat, von.lon, nach.lat, nach.lon, neuLaden]);

  return (
    <div className="verkehr">
      <h2>🚗 Live-Verkehr</h2>

      {/* Von / Nach */}
      <div className="verkehr-adressen">
        <AdressFeld label="Von" wert={von} setWert={(o) => setWahl({ ...wahl, von: o })} pins={pins} />
        <button className="tauschen" onClick={() => setWahl({ von: nach, nach: von })} aria-label="Richtung tauschen">
          ⇅
        </button>
        <AdressFeld label="Nach" wert={nach} setWert={(o) => setWahl({ ...wahl, nach: o })} pins={pins} />
      </div>

      {gleicherOrt && <p className="pendel-hinweis">Wähle zwei verschiedene Adressen.</p>}
      {fehler && <p className="fehler">{fehler}</p>}
      {!gleicherOrt && !route && !fehler && <p>Lade Verkehrsdaten …</p>}

      {route && !gleicherOrt && (
        <>
          {/* Grosse Karte */}
          <div className={`risiko-karte ${stufe(route.stau_min)}`}>
            <p className="label">Fahrzeit jetzt · Ankunft {route.ankunft}</p>
            <p className="wert">{dauerSchoen(route.dauer_min)}</p>
            <p>
              {route.stau_min > 0 ? `+${route.stau_min} Min. durch Stau` : "Kein Stau"}
              {" · "}leere Strassen: {dauerSchoen(route.ohne_stau_min)}
              {" · "}{route.distanz_km} km
            </p>
          </div>

          {/* Staustellen */}
          {route.staus.length > 0 && (
            <div className="stunden">
              {route.staus.map((s, i) => (
                <div className="stau" key={i}>
                  <span>⚠️ {s.art} nach {s.bei_km} km</span>
                  <span className="label">{s.tempo_kmh ? `${s.tempo_kmh} km/h` : ""}</span>
                  <span className={`bd ${stufe(s.verzoegerung_min)}`}>+{s.verzoegerung_min} Min.</span>
                </div>
              ))}
            </div>
          )}

          <div className="verkehr-fuss">
            <span>
              Stand {stand && stand.toLocaleTimeString("de-CH", { hour: "2-digit", minute: "2-digit" })} · Daten: TomTom
            </span>
            <button onClick={() => setNeuLaden(neuLaden + 1)}>🔄 Aktualisieren</button>
          </div>
        </>
      )}
    </div>
  );
}