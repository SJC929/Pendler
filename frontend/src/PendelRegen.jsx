import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const STUFEN = {
  trocken: { symbol: "🌤️", text: "trocken", rang: 0 },
  vielleicht: { symbol: "🌂", text: "vielleicht Regen", rang: 1 },
  regen: { symbol: "☔", text: "Regen", rang: 2 },
};

const WEGE = [
  { key: "hin", text: "🏠 → 🏢 Hinweg", name: "Hinweg" },
  { key: "heim", text: "🏢 → 🏠 Heimweg", name: "Heimweg" },
];

// Ort eindeutig machen (Name + Kanton)
const schluessel = (o) => `${o.name}|${o.canton}`;

// Schlechteres Wetter von zwei Orten (zuerst Stufe, dann Wahrscheinlichkeit)
function schlimmer(a, b) {
  if (!a) return b;
  if (STUFEN[b.stufe].rang !== STUFEN[a.stufe].rang) {
    return STUFEN[b.stufe].rang > STUFEN[a.stufe].rang ? b : a;
  }
  return b.wahrscheinlichkeit > a.wahrscheinlichkeit ? b : a;
}

// Einstellungen aus dem Browser laden
function ladeEinstellungen() {
  try {
    const gespeichert = localStorage.getItem("pendler-pendel");
    if (gespeichert) return JSON.parse(gespeichert);
  } catch {
    // Laden nicht möglich → Standard
  }
  return { hin: "07:30", heim: "17:00", wohnort: null, arbeitsort: null };
}

// Text für das Banner oben
function bannerText(regen) {
  const schlimmster = WEGE.map((w) => ({ ...w, info: regen[w.key] }))
    .filter((w) => w.info)
    .reduce((a, b) => (!a || schlimmer(a.info, b.info) === b.info ? b : a), null);
  if (!schlimmster) return { stufe: "trocken", text: "Keine Daten" };

  const { stufe, zeit, wahrscheinlichkeit, tag, ort } = schlimmster.info;
  const wann = `${tag === "morgen" ? "morgen " : ""}um ${zeit}`;

  if (stufe === "regen") {
    return { stufe, text: `☔ Schirm mitnehmen: Regen in ${ort} beim ${schlimmster.name} ${wann} (${wahrscheinlichkeit} %)` };
  }
  if (stufe === "vielleicht") {
    return { stufe, text: `🌂 Vielleicht Schirm einpacken: ${wahrscheinlichkeit} % in ${ort} beim ${schlimmster.name} ${wann}` };
  }
  return { stufe, text: "🌤️ Kein Regen auf deinen Pendelwegen" };
}

export default function PendelRegen({ pins, ort }) {
  const [einst, setEinst] = useState(ladeEinstellungen);
  const [regen, setRegen] = useState(null);
  const [fehler, setFehler] = useState(false);

  // Gespeicherten Ort in den Pins suchen, sonst Ersatz nehmen
  const finde = (key, ersatz) => pins.find((p) => schluessel(p) === key) || ersatz;
  const wohnort = finde(einst.wohnort, pins[0] || ort);
  const arbeitsort = finde(einst.arbeitsort, pins[1] || pins[0] || ort);
  const gleicherOrt = schluessel(wohnort) === schluessel(arbeitsort);

  // 🔔 Einstellungen merken
  useEffect(() => {
    try {
      localStorage.setItem("pendler-pendel", JSON.stringify(einst));
    } catch {
      // Speichern nicht möglich → ignorieren
    }
  }, [einst]);

  // 🔔 Regen für Wohnort und Arbeitsort holen
  useEffect(() => {
    if (!einst.hin || !einst.heim) return;
    setRegen(null);
    setFehler(false);

    const hole = (o) => {
      const parameter = new URLSearchParams({ lat: o.lat, lon: o.lon, hin: einst.hin, heim: einst.heim });
      return fetch(`${API_URL}/weather/commute?${parameter}`).then((antwort) => {
        if (!antwort.ok) throw new Error();
        return antwort.json();
      });
    };

    const timer = setTimeout(() => {
      Promise.all([hole(wohnort), gleicherOrt ? null : hole(arbeitsort)])
        .then(([daheim, arbeit]) => {
          const ergebnis = {};
          for (const weg of WEGE) {
            const kandidaten = [];
            if (daheim[weg.key]) kandidaten.push({ ...daheim[weg.key], ort: wohnort.name });
            if (arbeit && arbeit[weg.key]) kandidaten.push({ ...arbeit[weg.key], ort: arbeitsort.name });
            const schlimmster = kandidaten.reduce(schlimmer, null);
            ergebnis[weg.key] = schlimmster ? { ...schlimmster, alle: kandidaten } : null;
          }
          setRegen(ergebnis);
        })
        .catch(() => setFehler(true));
    }, 400);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wohnort.lat, wohnort.lon, arbeitsort.lat, arbeitsort.lon, einst.hin, einst.heim]);

  const banner = regen ? bannerText(regen) : null;

  return (
    <div className="pendel">
      {fehler && <p className="fehler">Die Regenwarnung ist gerade nicht verfügbar.</p>}
      {banner && <div className={`pendel-banner ${banner.stufe}`}>{banner.text}</div>}

      {/* Wohnort und Arbeitsort */}
      <div className="pendel-orte">
        <label>
          🏠 Wohnort
          <select value={schluessel(wohnort)} onChange={(e) => setEinst({ ...einst, wohnort: e.target.value })}>
            {pins.map((p) => (
              <option key={schluessel(p)} value={schluessel(p)}>{p.name}</option>
            ))}
          </select>
        </label>
        <label>
          🏢 Arbeitsort
          <select value={schluessel(arbeitsort)} onChange={(e) => setEinst({ ...einst, arbeitsort: e.target.value })}>
            {pins.map((p) => (
              <option key={schluessel(p)} value={schluessel(p)}>{p.name}</option>
            ))}
          </select>
        </label>
      </div>
      {pins.length < 2 && (
        <p className="pendel-hinweis">Tipp: Such oben deinen Arbeitsort und pinne ihn, dann kannst du ihn hier wählen.</p>
      )}

      {/* Hinweg und Heimweg */}
      <div className="pendel-wege">
        {WEGE.map((weg) => {
          const info = regen ? regen[weg.key] : null;
          return (
            <label className="pendel-weg" key={weg.key}>
              <span className="label">{weg.text}</span>
              <input
                type="time"
                value={einst[weg.key]}
                onChange={(e) => setEinst({ ...einst, [weg.key]: e.target.value })}
              />
                {info && (
                <span className={`pendel-stufe ${info.stufe}`}>
                  {STUFEN[info.stufe].symbol} {STUFEN[info.stufe].text}
                  {info.alle.map((k) => ` · ${k.ort} ${k.wahrscheinlichkeit} %`).join("")}
                  {info.tag === "morgen" ? " (morgen)" : ""}
                </span>
              )}
            </label>
          );
        })}
      </div>
    </div>
  );
}