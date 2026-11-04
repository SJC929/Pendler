import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const ANZAHL_STUNDEN = 4;
const FEHLER_TEXT = "Die Prognose ist gerade nicht verfügbar. Bitte später nochmals versuchen.";

// Risiko in Prozent → Farbe
const stufe = (r) => (r >= 35 ? "hoch" : r >= 15 ? "mittel" : "tief");
const zweistellig = (z) => String(z).padStart(2, "0");

// In Basel sind die Linien unter 30 Trams, die anderen Busse
function fahrzeug(linie) {
  const nummer = parseInt(linie, 10);
  return !isNaN(nummer) && nummer < 30 ? "🚋" : "🚌";
}

function lokalesDatum(d) {
  return `${d.getFullYear()}-${zweistellig(d.getMonth() + 1)}-${zweistellig(d.getDate())}`;
}

function naechsteTage() {
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() + i);
    return lokalesDatum(d);
  });
}

function tagLabel(datum, i) {
  if (i === 0) return "Heute";
  if (i === 1) return "Morgen";
  return new Date(datum).toLocaleDateString("de-CH", { weekday: "short", day: "numeric", month: "numeric" });
}

function ladeStation() {
  try {
    return localStorage.getItem("pendler-station") || "";
  } catch {
    return "";
  }
}

export default function StationPrognose() {
  const tage = naechsteTage();
  const [station, setStation] = useState(ladeStation);
  const [suche, setSuche] = useState("");
  const [vorschlaege, setVorschlaege] = useState([]);
  const [tag, setTag] = useState(tage[0]);
  const [ab, setAb] = useState(Math.max(5, new Date().getHours()));
  const [daten, setDaten] = useState(null);
  const [fehler, setFehler] = useState("");

  // 🔔 Station merken
  useEffect(() => {
    try {
      localStorage.setItem("pendler-station", station);
    } catch {
      // Speichern nicht möglich → ignorieren
    }
  }, [station]);

  // 🔔 Haltestellen vorschlagen, während man tippt
  useEffect(() => {
    if (suche.length < 2) {
      setVorschlaege([]);
      return;
    }
    const timer = setTimeout(() => {
      fetch(`${API_URL}/predict/station/search?q=${encodeURIComponent(suche)}`)
        .then((antwort) => (antwort.ok ? antwort.json() : []))
        .then((liste) => setVorschlaege(liste))
        .catch(() => setVorschlaege([]));
    }, 300);
    return () => clearTimeout(timer);
  }, [suche]);

  // 🔔 Prognose holen, wenn Station oder Tag ändert
  useEffect(() => {
    if (!station) return;
    setDaten(null);
    setFehler("");
    const parameter = new URLSearchParams({ haltestelle: station, datum: tag });
    fetch(`${API_URL}/predict/station?${parameter}`)
      .then((antwort) => {
        if (!antwort.ok) throw new Error();
        return antwort.json();
      })
      .then((d) => setDaten(d))
      .catch(() => setFehler(FEHLER_TEXT));
  }, [station, tag]);

  function waehle(name) {
    setStation(name);
    setSuche("");
    setVorschlaege([]);
  }

  // Welche Stunden zeigen wir? z.B. ab 10 → 10, 11, 12, 13
  const stunden = Array.from({ length: ANZAHL_STUNDEN }, (_, i) => ab + i).filter((s) => s <= 23);
  const linien = daten
    ? daten.linien.filter((l) => l.stunden.some((s) => stunden.includes(s.stunde)))
    : [];

  return (
    <div className="station">
      <h2>🔮 Kommt mein Tram pünktlich?</h2>
      <p className="station-untertitel">Alle Trams und Busse in Basel · Prognose für 7 Tage</p>

      {/* Haltestelle */}
      <div className="adress-feld">
        <input
          type="text"
          className="station-suche"
          placeholder={station ? `🚏 ${station}` : "🚏 Haltestelle suchen, z. B. Aeschenplatz"}
          value={suche}
          onChange={(e) => setSuche(e.target.value)}
        />
        {vorschlaege.length > 0 && (
          <ul className="adress-liste">
            {vorschlaege.map((v) => (
              <li key={v} onClick={() => waehle(v)}>🚏 {v}</li>
            ))}
          </ul>
        )}
      </div>

      {station && (
        <>
          {/* Tag + Uhrzeit */}
          <div className="station-steuerung">
            <div className="tage">
              {tage.map((d, i) => (
                <button key={d} className={d === tag ? "aktiv" : ""} onClick={() => setTag(d)}>
                  {tagLabel(d, i)}
                </button>
              ))}
            </div>
            <label className="station-ab">
              ab
              <select value={ab} onChange={(e) => setAb(Number(e.target.value))}>
                {Array.from({ length: 19 }, (_, i) => i + 5).map((s) => (
                  <option key={s} value={s}>{zweistellig(s)}:00</option>
                ))}
              </select>
            </label>
          </div>

          {/* Legende oben */}
          <div className="station-legende">
            <span><i className="punkt tief" /> pünktlich</span>
            <span><i className="punkt mittel" /> manchmal zu spät</span>
            <span><i className="punkt hoch" /> oft zu spät</span>
          </div>
          <p className="station-erklaerung">Die Zahl = Chance, dass es mehr als 3 Minuten zu spät ist.</p>

          {fehler && <p className="fehler">{fehler}</p>}
          {!daten && !fehler && <p>Lade Prognose …</p>}
          {daten && linien.length === 0 && <p>Zu dieser Zeit fahren hier keine Trams oder Busse.</p>}

          {/* Tabelle */}
          {linien.length > 0 && (
            <div className="station-tabelle">
              <div className="station-zeile station-kopf">
                <span>Linie</span>
                <span>Richtung</span>
                {stunden.map((s) => (
                  <span key={s} className="station-zeit">{zweistellig(s)}:00</span>
                ))}
              </div>

              {linien.map((l) => (
                <div className="station-zeile" key={`${l.betreiber}-${l.linie}-${l.ziel}`}>
                  <span className="station-linie">{fahrzeug(l.linie)} {l.linie}</span>
                  <span className="station-ziel" title={l.ziel}>{l.ziel}</span>
                  {stunden.map((s) => {
                    const eintrag = l.stunden.find((x) => x.stunde === s);
                    return (
                      <span key={s} className={`zelle ${eintrag ? stufe(eintrag.risiko) : "leer"}`}>
                        {eintrag ? `${eintrag.risiko}%` : "–"}
                      </span>
                    );
                  })}
                </div>
              ))}
            </div>
          )}

          <p className="prognose-info">
            Echte Fahrdaten von BVB und BLT · Wetter und Schulferien · jede Nacht neu berechnet · ohne Gewähr
          </p>
        </>
      )}
    </div>
  );
}