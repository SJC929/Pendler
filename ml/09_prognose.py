"""
Erstellt die Verspätungsprognose für Bus 48 (BVB) für die nächsten 7 Tage.

1. Trainiert das Risiko-Modell (> 3 Min. zu spät) mit allen gesammelten Daten
2. Holt die Wetterprognose (Open-Meteo) und die Schulferien (OpenHolidays)
3. Berechnet das Risiko für jede Haltestelle, Richtung und Stunde
4. Speichert alles in prognosen/bus48.json (wird später von FastAPI gelesen)
"""
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from sklearn.ensemble import HistGradientBoostingClassifier

ML = Path(__file__).resolve().parent
DATEN = ML / "data" / "bus48_modell.csv"
AUSGABE = ML.parent / "prognosen" / "bus48.json"

SCHWEIZ = ZoneInfo("Europe/Zurich")   # GitHub läuft in UTC → Schweizer Zeit fest vorgeben
TAGE = 7
LAT, LON = 47.56, 7.59
SCHWELLE_MIN = 3

ZAHLEN = ["stunde", "wochentag", "wochenende", "schulferien", "temp", "regen_mm"]
KATEGORIEN = ["HALTESTELLEN_NAME", "richtung"]


def heute():
    """Heutiges Datum in der Schweiz."""
    return datetime.now(SCHWEIZ).date()


def merkmale(tabelle, spalten=None):
    """Text-Spalten in 0/1-Spalten umwandeln (One-Hot-Encoding)."""
    X = pd.get_dummies(tabelle[ZAHLEN + KATEGORIEN], columns=KATEGORIEN, dtype=int)
    if spalten is not None:
        X = X.reindex(columns=spalten, fill_value=0)
    return X


def modell_trainieren():
    daten = pd.read_csv(DATEN, parse_dates=["tag", "planzeit"])
    daten["zu_spaet"] = (daten["verspaetung_min"] > SCHWELLE_MIN).astype(int)

    X = merkmale(daten)
    modell = HistGradientBoostingClassifier(random_state=42)
    modell.fit(X, daten["zu_spaet"])

    print(f"✅ Modell trainiert: {len(daten)} Abfahrten, {daten['tag'].nunique()} Tage")
    return modell, X.columns, daten


def wetter_holen():
    """Wetterprognose holen – bei Zeitüberschreitung bis zu 3 Versuche."""
    for versuch in range(1, 4):
        try:
            antwort = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": LAT, "longitude": LON,
                    "hourly": "temperature_2m,precipitation",
                    "timezone": "Europe/Zurich", "forecast_days": TAGE,
                },
                timeout=30,
            )
            antwort.raise_for_status()
            break
        except requests.RequestException:
            if versuch == 3:
                raise
            print(f"⏳ Open-Meteo antwortet nicht (Versuch {versuch}/3), warte 10 s …")
            time.sleep(10)

    stunden = antwort.json()["hourly"]
    wetter = pd.DataFrame({
        "zeit": pd.to_datetime(stunden["time"]),
        "temp": stunden["temperature_2m"],
        "regen_mm": stunden["precipitation"],
    })
    print(f"✅ Wetterprognose: {len(wetter)} Stunden")
    return wetter


def ferientage_holen(von, bis):
    antwort = requests.get(
        "https://openholidaysapi.org/SchoolHolidays",
        params={
            "countryIsoCode": "CH", "subdivisionCode": "CH-BS", "languageIsoCode": "DE",
            "validFrom": von.isoformat(), "validTo": bis.isoformat(),
        },
        headers={"accept": "application/json"},
        timeout=30,
    )
    antwort.raise_for_status()

    ferien = set()
    for f in antwort.json():
        for d in pd.date_range(f["startDate"], f["endDate"]):
            ferien.add(d)
    print(f"✅ Schulferien: {len(ferien)} Tage im Zeitraum")
    return ferien


def zeilen_bauen(daten, wetter, ferien):
    # Welche Haltestellen fährt der Bus pro Richtung an, und zu welchen Stunden?
    kombis = daten[["richtung", "HALTESTELLEN_NAME", "stunde"]].drop_duplicates()

    tage = pd.DataFrame({"tag": pd.date_range(heute(), periods=TAGE)})
    zeilen = tage.merge(kombis, how="cross")

    zeilen["wochentag"] = zeilen["tag"].dt.day_of_week        # 0 = Montag
    zeilen["wochenende"] = zeilen["wochentag"] >= 5
    zeilen["schulferien"] = zeilen["tag"].isin(ferien)

    # Jede Zeile bekommt das Wetter ihrer Stunde
    zeilen["zeit"] = zeilen["tag"] + pd.to_timedelta(zeilen["stunde"], unit="h")
    zeilen = zeilen.merge(wetter, on="zeit", how="left")
    return zeilen


def speichern(zeilen):
    aus = zeilen[["tag", "stunde", "richtung", "HALTESTELLEN_NAME", "risiko"]].rename(
        columns={"tag": "datum", "HALTESTELLEN_NAME": "haltestelle"}
    )
    aus["datum"] = aus["datum"].dt.strftime("%Y-%m-%d")
    aus = aus.sort_values(["datum", "richtung", "haltestelle", "stunde"])

    inhalt = {
        "linie": "48",
        "betreiber": "BVB",
        "erstellt": datetime.now(SCHWEIZ).isoformat(timespec="minutes"),
        "schwelle_min": SCHWELLE_MIN,
        "prognosen": aus.to_dict("records"),
    }
    AUSGABE.parent.mkdir(exist_ok=True)
    AUSGABE.write_text(json.dumps(inhalt, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Gespeichert: {AUSGABE} ({len(aus)} Prognosen, {AUSGABE.stat().st_size // 1024} KB)")


def main():
    modell, spalten, daten = modell_trainieren()
    wetter = wetter_holen()

    start = heute()
    ferien = ferientage_holen(start, start + pd.Timedelta(days=TAGE))

    zeilen = zeilen_bauen(daten, wetter, ferien)
    zeilen["risiko"] = modell.predict_proba(merkmale(zeilen, spalten))[:, 1].round(2)

    speichern(zeilen)

    print("\n🔴 Höchstes Risiko in den nächsten 7 Tagen:")
    top = zeilen.nlargest(5, "risiko")
    for z in top.itertuples():
        print(f"   {z.tag:%a %d.%m.} {z.stunde:02d} Uhr  {z.HALTESTELLEN_NAME:22s} "
              f"{z.richtung:14s} {z.risiko:.0%}")


if __name__ == "__main__":
    main()