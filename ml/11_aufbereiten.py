"""
Bereitet die gesammelten Bus-48-Daten für das Modell auf (wie Notebook 06).

1. Alle Tagesdateien laden, Richtung bestimmen
2. Verspätung pro Abfahrt berechnen
3. Wetter (MeteoSwiss) und Schulferien (OpenHolidays) dazunehmen
4. Speichern in ml/data/bus48_modell.csv
"""
from pathlib import Path

import pandas as pd
import requests

ML = Path(__file__).resolve().parent
LINIE = ML / "data" / "linie"
AUSGABE = ML / "data" / "bus48_modell.csv"

STADT_ZIELE = ["Bahnhof SBB", "Bahnhof St.Johann"]
WETTER_URL = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/bas/ogd-smn_bas_h_recent.csv"
WETTER_CODES = {"tre200h0": "temp", "rre150h0": "regen_mm"}

SPALTEN = ["tag", "planzeit", "HALTESTELLEN_NAME", "richtung", "stunde", "wochentag",
           "wochenende", "schulferien", "temp", "regen_mm", "verspaetung_min"]


def fahrten_laden():
    dateien = sorted(LINIE.glob("*_linie_48.csv"))
    alle = pd.concat([pd.read_csv(p, dtype=str) for p in dateien], ignore_index=True)

    alle["tag"] = pd.to_datetime(alle["BETRIEBSTAG"], format="mixed", dayfirst=True)
    # Planzeit: normalerweise die Abfahrt, an der Endhaltestelle gibt es nur eine Ankunft
    alle["planzeit"] = pd.to_datetime(
        alle["ABFAHRTSZEIT"].fillna(alle["ANKUNFTSZEIT"]), format="mixed", dayfirst=True
    )
    # Eine Fahrt eindeutig machen: dieselbe Fahrtnummer gibt es an jedem Tag
    alle["fahrt"] = alle["BETRIEBSTAG"] + "_" + alle["FAHRT_BEZEICHNER"]

    # Richtung: der letzte Halt einer Fahrt ist ihr Ziel
    alle = alle.sort_values(["fahrt", "planzeit"])
    ziel = alle.groupby("fahrt")["HALTESTELLEN_NAME"].last()
    alle["richtung"] = alle["fahrt"].map(ziel).apply(
        lambda z: "stadteinwärts" if z in STADT_ZIELE else "stadtauswärts"
    )

    print(f"✅ Geladen: {alle['tag'].nunique()} Tage, {alle['fahrt'].nunique()} Fahrten")
    return alle


def verspaetung_berechnen(alle):
    gemessen = alle[alle["AB_PROGNOSE_STATUS"] == "REAL"].copy()
    gemessen["ist"] = pd.to_datetime(gemessen["AB_PROGNOSE"], format="mixed", dayfirst=True)
    gemessen["verspaetung_min"] = (gemessen["ist"] - gemessen["planzeit"]).dt.total_seconds() / 60

    # Messfehler weglassen: mehr als 2 Min. zu früh oder über 30 Min. zu spät
    gemessen = gemessen[gemessen["verspaetung_min"].between(-2, 30)]

    gemessen["stunde"] = gemessen["planzeit"].dt.hour
    gemessen["wochentag"] = gemessen["tag"].dt.day_of_week      # 0 = Montag
    gemessen["wochenende"] = gemessen["wochentag"] >= 5
    print(f"✅ Gemessene Abfahrten: {len(gemessen)}")
    return gemessen


def wetter_dazu(gemessen):
    roh = pd.read_csv(WETTER_URL, sep=";")
    # MeteoSwiss misst in UTC → in Schweizer Zeit umrechnen
    roh["zeit"] = (
        pd.to_datetime(roh["reference_timestamp"], format="%d.%m.%Y %H:%M")
        .dt.tz_localize("UTC").dt.tz_convert("Europe/Zurich").dt.tz_localize(None)
    )
    wetter = roh[["zeit", *WETTER_CODES]].rename(columns=WETTER_CODES)
    wetter = wetter.drop_duplicates("zeit")   # Zeitumstellung Ende Oktober: doppelte Stunde

    gemessen["zeit"] = gemessen["planzeit"].dt.floor("h")
    gemessen = gemessen.merge(wetter, on="zeit", how="left")
    print(f"✅ Wetter dazu: {gemessen['temp'].isna().sum()} Abfahrten ohne Wetter")
    return gemessen


def ferien_dazu(gemessen):
    antwort = requests.get(
        "https://openholidaysapi.org/SchoolHolidays",
        params={
            "countryIsoCode": "CH", "subdivisionCode": "CH-BS", "languageIsoCode": "DE",
            "validFrom": gemessen["tag"].min().strftime("%Y-%m-%d"),
            "validTo": gemessen["tag"].max().strftime("%Y-%m-%d"),
        },
        headers={"accept": "application/json"},
        timeout=30,
    )
    antwort.raise_for_status()

    ferien_tage = set()
    for ferien in antwort.json():
        for d in pd.date_range(ferien["startDate"], ferien["endDate"]):
            ferien_tage.add(d)

    gemessen["schulferien"] = gemessen["tag"].isin(ferien_tage)
    print(f"✅ Schulferien: {gemessen.loc[gemessen['schulferien'], 'tag'].nunique()} Tage")
    return gemessen


def main():
    alle = fahrten_laden()
    gemessen = verspaetung_berechnen(alle)
    gemessen = wetter_dazu(gemessen)
    gemessen = ferien_dazu(gemessen)

    gemessen[SPALTEN].to_csv(AUSGABE, index=False)
    print(f"🏁 Gespeichert: {len(gemessen)} Abfahrten → {AUSGABE.name}")


if __name__ == "__main__":
    main()