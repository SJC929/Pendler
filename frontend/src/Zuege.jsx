import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// Verkehrsmittel → Symbol und Name
const FAHRZEUG = {
  train: { symbol: "🚆", name: "" },
  tram: { symbol: "🚋", name: "Tram" },
  bus: { symbol: "🚌", name: "Bus" },
  ship: { symbol: "⛴️", name: "Schiff" },
};

// Heutiges Datum als "2026-11-02"
function heuteDatum() {
  const d = new Date();
  const monat = String(d.getMonth() + 1).padStart(2, "0");
  const tag = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${monat}-${tag}`;
}

// Aktuelle Uhrzeit als "09:51"
function aktuelleZeit() {
  const d = new Date();
  const stunden = String(d.getHours()).padStart(2, "0");
  const minuten = String(d.getMinutes()).padStart(2, "0");
  return `${stunden}:${minuten}`;
}

// Gepinnte Routen aus dem Browser laden
function ladeRouten() {
  try {
    const gespeichert = localStorage.getItem("pendler-routen");
    return gespeichert ? JSON.parse(gespeichert) : [];
  } catch {
    return [];
  }
}

// Gleiche Route? (von + nach + zeit vergleichen)
function gleicheRoute(a, b) {
  return a.von === b.von && a.nach === b.nach && a.zeit === b.zeit;
}

// 🧱 Kleiner Baustein: Eingabefeld mit Haltestellen-Vorschlägen
function StationFeld({ platzhalter, wert, setWert }) {
  const [vorschlaege, setVorschlaege] = useState([]);
  const [offen, setOffen] = useState(false);

  useEffect(() => {
    if (!offen || wert.length < 2) {
      setVorschlaege([]);
      return;
    }
    const timer = setTimeout(() => {
      fetch(`${API_URL}/stations/search?q=${encodeURIComponent(wert)}`)
        .then((daten) => setVorschlaege(Array.isArray(daten) ? daten : []))
        .catch(() => setVorschlaege([]));
    }, 300);
    return () => clearTimeout(timer);
  }, [wert, offen]);

  return (
    <div className="suche station">
      <input
        type="text"
        placeholder={platzhalter}
        value={wert}
        onChange={(e) => {
          setWert(e.target.value);
          setOffen(true);
        }}
      />
      {offen && vorschlaege.length > 0 && (
        <ul className="vorschlaege">
          {vorschlaege.map((station) => (
            <li
              key={station.id}
              onClick={() => {
                setWert(station.name);
                setOffen(false);
                setVorschlaege([]);
              }}
            >
              🚉 {station.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// 🧱 Grosser Baustein: Meine Verbindungen
export default function Zuege() {
  const [routen, setRouten] = useState(ladeRouten);
  const [aktiv, setAktiv] = useState(() => ladeRouten()[0] || null);
  const [von, setVon] = useState("");
  const [nach, setNach] = useState("");
  const [zeit, setZeit] = useState("07:00");
  const [jetztZeit, setJetztZeit] = useState(null);
  const [verbindungen, setVerbindungen] = useState(null);
  const [fehler, setFehler] = useState(false);

  // Welche Startzeit gilt gerade? «Jetzt» hat Vorrang vor der Pin-Zeit
  const startZeit = jetztZeit || (aktiv ? aktiv.zeit : null);

  // 🔔 Routen im Browser speichern
  useEffect(() => {
    try {
      localStorage.setItem("pendler-routen", JSON.stringify(routen));
    } catch {
      // Speichern nicht möglich → ignorieren
    }
  }, [routen]);

  // 🔔 Verbindungen holen, sobald Route oder Startzeit wechselt
  useEffect(() => {
    if (aktiv === null) return;
    setVerbindungen(null);
    setFehler(false);

    const parameter = new URLSearchParams({
      von: aktiv.von,
      nach: aktiv.nach,
      date: heuteDatum(),
      time: startZeit,
    });

    fetch(`${API_URL}/connections?${parameter}`)
      .then((antwort) => {
        if (!antwort.ok) throw new Error("Fehler");
        return antwort.json();
      })
      .then((daten) => setVerbindungen(daten))
      .catch(() => setFehler(true));
  }, [aktiv, startZeit]);

  // Knopf «Jetzt»
  function abJetzt() {
    const jetzt = aktuelleZeit();
    setZeit(jetzt);
    setJetztZeit(jetzt);
  }

  // Route auswählen (zurück zur gepinnten Zeit)
  function waehleRoute(route) {
    setAktiv(route);
    setJetztZeit(null);
  }

  // Route pinnen
  function routePinnen() {
    if (von === "" || nach === "") return;
    const neueRoute = { von, nach, zeit };
    if (!routen.some((r) => gleicheRoute(r, neueRoute))) {
      setRouten([...routen, neueRoute]);
    }
    waehleRoute(neueRoute);
    setVon("");
    setNach("");
  }

  // Route entfernen
  function routeEntfernen(route) {
    const rest = routen.filter((r) => !gleicheRoute(r, route));
    setRouten(rest);
    if (aktiv !== null && gleicheRoute(aktiv, route)) {
      waehleRoute(rest[0] || null);
    }
  }

  return (
    <section className="zuege">
      <h3>🚆 Meine Verbindungen</h3>

      {/* Neue Route */}
      <div className="route-form">
        <StationFeld platzhalter="Von, z. B. Basel SBB" wert={von} setWert={setVon} />
        <StationFeld platzhalter="Nach, z. B. Luzern" wert={nach} setWert={setNach} />
        <div className="zeit-gruppe">
          <input
            type="time"
            className="zeit"
            value={zeit}
            onChange={(e) => setZeit(e.target.value)}
          />
          <button className="jetzt-button" onClick={abJetzt}>
            🕐 Jetzt
          </button>
        </div>
        <button className="pin-button" onClick={routePinnen}>
          📌 Route pinnen
        </button>
      </div>

      {/* Gepinnte Routen */}
      <div className="pins">
        {routen.map((route) => (
          <span
            key={`${route.von}-${route.nach}-${route.zeit}`}
            className={aktiv !== null && gleicheRoute(route, aktiv) ? "pin aktiv" : "pin"}
            onClick={() => waehleRoute(route)}
          >
            🚆 {route.von} → {route.nach} · {route.zeit}
            <button
              className="pin-x"
              onClick={(e) => {
                e.stopPropagation();
                routeEntfernen(route);
              }}
            >
              ✕
            </button>
          </span>
        ))}
      </div>

      {/* Hinweise */}
      {aktiv === null && (
        <p className="hinweis">Pinne eine Route, um deine Verbindungen zu sehen.</p>
      )}
      {aktiv !== null && verbindungen === null && !fehler && <p>Lade Verbindungen …</p>}
      {fehler && (
        <p className="hinweis">
          Der Fahrplan ist gerade nicht erreichbar. Versuch es in ein paar Minuten nochmals.
        </p>
      )}

      {/* Verbindungen */}
      {aktiv !== null && verbindungen !== null && (
        <>
          <p className="hinweis">
            {jetztZeit
              ? `Abfahrten ab jetzt (${jetztZeit} Uhr), für die nächsten 3 Stunden`
              : `Abfahrten ab ${aktiv.zeit} Uhr, für die nächsten 3 Stunden`}
          </p>
          {verbindungen.length === 0 && <p>Keine Verbindungen in diesem Zeitraum.</p>}
          <ul className="verbindungen">
            {verbindungen.map((v, i) => {
              const fahrzeug = FAHRZEUG[v.type] || FAHRZEUG.train;
              return (
                <li key={i} className="verbindung">
                  <div className="zeiten">
                    <strong>{v.departure}</strong> → {v.arrival}
                  </div>
                  <div className="details">
                    {/* Gleis nur bei Zügen */}
                    {v.type === "train" && v.platform && (
                      <span className="gleis">Gleis {v.platform}</span>
                    )}
                    <span className="linie">
                      {fahrzeug.symbol} {fahrzeug.name} {v.line}
                    </span>
                    <span>{v.duration}</span>
                    <span>{v.transfers === 0 ? "direkt" : `${v.transfers}× umsteigen`}</span>
                  </div>
                  <div className={v.delay ? "status verspaetet" : "status"}>
                    {v.delay ? `+${v.delay}'` : "pünktlich"}
                  </div>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </section>
  );
}