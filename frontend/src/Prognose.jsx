import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const RICHTUNGEN = [
  { key: "stadteinwärts", text: "→ Stadt" },
  { key: "stadtauswärts", text: "→ Bachgraben" },
];

const FEHLER_TEXT = "Die Prognose ist gerade nicht verfügbar. Bitte später nochmals versuchen.";

// Risiko → Farbe und Tipp
function stufe(risiko) {
  if (risiko >= 0.35) return { key: "hoch", text: "Hohes Risiko", tipp: "lieber einen Bus früher nehmen" };
  if (risiko >= 0.15) return { key: "mittel", text: "Mittleres Risiko", tipp: "etwas Puffer einplanen" };
  return { key: "tief", text: "Tiefes Risiko", tipp: "der Bus kommt meist pünktlich" };
}

// Datum als "2026-11-03" (Schweizer Zeit, nicht UTC)
function lokalesDatum(d) {
  const monat = String(d.getMonth() + 1).padStart(2, "0");
  const tag = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${monat}-${tag}`;
}

// "2026-11-05" → "Heute" / "Morgen" / "Do., 5.11."
function tagLabel(datum) {
  const heute = new Date();
  const morgen = new Date();
  morgen.setDate(heute.getDate() + 1);
  if (datum === lokalesDatum(heute)) return "Heute";
  if (datum === lokalesDatum(morgen)) return "Morgen";
  return new Date(datum).toLocaleDateString("de-CH", { weekday: "short", day: "numeric", month: "numeric" });
}

// Busbetrieb beginnt um ca. 5 Uhr → 0 Uhr kommt ans Ende des Tages
function reihenfolge(stunde) {
  return (stunde + 24 - 4) % 24;
}

const zweistellig = (zahl) => String(zahl).padStart(2, "0");
const prozent = (risiko) => `${Math.round(risiko * 100)} %`;

// Gewählte Richtung + Haltestelle aus dem Browser laden
function ladeWahl() {
  try {
    const gespeichert = localStorage.getItem("pendler-prognose");
    return gespeichert ? JSON.parse(gespeichert) : { richtung: "stadteinwärts", haltestelle: "Ziegelei" };
  } catch {
    return { richtung: "stadteinwärts", haltestelle: "Ziegelei" };
  }
}

export default function Prognose() {
  // 📝 Gedächtnis
  const [wahl, setWahl] = useState(ladeWahl);
  const [haltestellen, setHaltestellen] = useState(null);
  const [prognose, setPrognose] = useState(null);
  const [tag, setTag] = useState(lokalesDatum(new Date()));
  const [fehler, setFehler] = useState("");

  // 🔔 Wahl merken
  useEffect(() => {
    try {
      localStorage.setItem("pendler-prognose", JSON.stringify(wahl));
    } catch {
      // Speichern nicht möglich → ignorieren
    }
  }, [wahl]);

  // 🔔 Haltestellen einmal laden
  useEffect(() => {
    fetch(`${API_URL}/predict/delay/stops`)
      .then((antwort) => {
        if (!antwort.ok) throw new Error();
        return antwort.json();
      })
      .then((daten) => setHaltestellen(daten.richtungen))
      .catch(() => setFehler(FEHLER_TEXT));
  }, []);

  // Haltestelle gibt es in dieser Richtung nicht? → erste nehmen
  const liste = haltestellen ? haltestellen[wahl.richtung] || [] : [];
  const haltestelle = liste.includes(wahl.haltestelle) ? wahl.haltestelle : liste[0];

  // 🔔 Prognose laden, sobald Haltestelle oder Richtung ändert
  useEffect(() => {
    if (!haltestelle) return;
    setPrognose(null);
    const parameter = new URLSearchParams({ haltestelle, richtung: wahl.richtung });
    fetch(`${API_URL}/predict/delay?${parameter}`)
      .then((antwort) => {
        if (!antwort.ok) throw new Error();
        return antwort.json();
      })
      .then((daten) => {
        setPrognose(daten);
        setFehler("");
      })
      .catch(() => setFehler(FEHLER_TEXT));
  }, [haltestelle, wahl.richtung]);

  // 🧮 Was zeigen wir an?
  const heute = lokalesDatum(new Date());
  const jetztStunde = new Date().getHours();
  const tage = prognose ? [...new Set(prognose.stunden.map((s) => s.datum))].filter((d) => d >= heute) : [];
  const aktiverTag = tage.includes(tag) ? tag : tage[0];

  let stunden = prognose ? prognose.stunden.filter((s) => s.datum === aktiverTag) : [];
  stunden.sort((a, b) => reihenfolge(a.stunde) - reihenfolge(b.stunde));
  if (aktiverTag === heute) {
    stunden = stunden.filter((s) => reihenfolge(s.stunde) >= reihenfolge(jetztStunde));
  }
  const naechste = aktiverTag === heute ? stunden[0] : null;

  // 🖥️ Die Seite
  return (
    <div className="prognose">
      <h2>
        🔮 Verspätungsprognose <span className="kanton">Bus 48 · BVB</span>
      </h2>
      <p className="prognose-intro">
        Wie wahrscheinlich ist der Bus mehr als {prognose ? prognose.schwelle_min : 3} Minuten zu spät?
      </p>

      {fehler && <p className="fehler">{fehler}</p>}

      {/* Richtung */}
      <div className="umschalter">
        {RICHTUNGEN.map((r) => (
          <button
            key={r.key}
            className={wahl.richtung === r.key ? "aktiv" : ""}
            onClick={() => setWahl({ ...wahl, richtung: r.key })}
          >
            {r.text}
          </button>
        ))}
      </div>

      {/* Haltestelle */}
      {haltestellen && (
        <label className="prognose-halt">
          🚏 Haltestelle
          <select value={haltestelle} onChange={(e) => setWahl({ ...wahl, haltestelle: e.target.value })}>
            {liste.map((h) => (
              <option key={h}>{h}</option>
            ))}
          </select>
        </label>
      )}

      {!prognose && !fehler && <p>Lade Prognose …</p>}

      {prognose && (
        <>
          {/* Tage */}
          <div className="tage">
            {tage.map((d) => (
              <button key={d} className={d === aktiverTag ? "aktiv" : ""} onClick={() => setTag(d)}>
                {tagLabel(d)}
              </button>
            ))}
          </div>

          {/* Grosse Karte: nächste Stunde */}
          {naechste && (
            <div className={`risiko-karte ${stufe(naechste.risiko).key}`}>
              <p className="label">Nächste Stunde · {zweistellig(naechste.stunde)}:00</p>
              <p className="wert">{prozent(naechste.risiko)}</p>
              <p>
                {stufe(naechste.risiko).text} – {stufe(naechste.risiko).tipp}
              </p>
            </div>
          )}

          {/* Balken pro Stunde */}
          {stunden.length === 0 ? (
            <p>Heute fahren keine Busse mehr. Wähle oben «Morgen».</p>
          ) : (
            <div className="stunden">
              {stunden.map((s) => (
                <div className="stunde" key={s.stunde}>
                  <span>{zweistellig(s.stunde)}:00</span>
                  <div className="balken-bahn">
                    <div
                      className={`balken ${stufe(s.risiko).key}`}
                      style={{ width: `${Math.max(s.risiko * 100, 2)}%` }}
                    />
                  </div>
                  <span className="stunde-wert">{prozent(s.risiko)}</span>
                </div>
              ))}
            </div>
          )}

            <div className="legende">
            <span><i className="punkt tief" /> unter 15 %</span>
            <span><i className="punkt mittel" /> 15–34 %</span>
            <span><i className="punkt hoch" /> ab 35 %</span>
          </div>

          <p className="prognose-info">
            Machine-Learning-Modell (Gradient Boosting), trainiert mit 3 Monaten echten Fahrdaten von
            opentransportdata.swiss, Wetter und Schulferien. Stand:{" "}
            {new Date(prognose.erstellt).toLocaleString("de-CH", {
              day: "numeric",
              month: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
            . Ohne Gewähr.
          </p>
        </>
      )}
    </div>
  );
}