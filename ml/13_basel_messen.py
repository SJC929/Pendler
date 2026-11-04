"""Misst, wie gross die Ist-Daten für alle Basler Trams und Busse (BVB + BLT) pro Tag sind."""
import importlib
import tempfile
from pathlib import Path

import pandas as pd
import requests

sammeln = importlib.import_module("10_sammeln")   # Funktionen aus 10_sammeln.py wiederverwenden

BETREIBER = ["BVB", "BLT"]
DB_LIMIT_MB = 1024
BYTES_PRO_ZEILE = 150          # grobe Schätzung für eine Zeile in PostgreSQL (inkl. Index)


def main():
    token = sammeln.lade_token()
    dateien = sammeln.tagesdateien(token)
    datum, url = list(dateien.items())[-1]
    print(f"📅 Messe den Tag {datum} …")

    teile = []
    with tempfile.TemporaryDirectory() as ordner:
        pfad = Path(ordner) / "tag.csv"
        with requests.get(url, stream=True, timeout=300) as antwort:
            antwort.raise_for_status()
            with open(pfad, "wb") as datei:
                for stueck in antwort.iter_content(1024 * 1024):
                    datei.write(stueck)
        for chunk in pd.read_csv(pfad, sep=";", dtype=str, usecols=sammeln.SPALTEN, chunksize=500_000):
            teile.append(chunk[chunk["BETREIBER_ABK"].isin(BETREIBER)])

    basel = pd.concat(teile, ignore_index=True)
    gemessen = basel[basel["AB_PROGNOSE_STATUS"] == "REAL"]

    # Ziel jeder Fahrt = letzte Haltestelle (wie bei Bus 48 die Richtung)
    basel["zeit"] = pd.to_datetime(basel["ABFAHRTSZEIT"].fillna(basel["ANKUNFTSZEIT"]), format="mixed", dayfirst=True)
    basel["fahrt"] = basel["BETRIEBSTAG"] + "_" + basel["FAHRT_BEZEICHNER"]
    ziel = basel.sort_values("zeit").groupby("fahrt")["HALTESTELLEN_NAME"].last()
    basel["ziel"] = basel["fahrt"].map(ziel)
    basel["stunde"] = basel["zeit"].dt.hour
    zusammengefasst = basel.drop_duplicates(["LINIEN_TEXT", "HALTESTELLEN_NAME", "ziel", "stunde"])

    roh_mb_monat = len(basel) * BYTES_PRO_ZEILE * 30 / 1024 / 1024
    zus_mb_monat = len(zusammengefasst) * BYTES_PRO_ZEILE * 30 / 1024 / 1024

    print("\n📊 Ergebnis für einen Tag")
    print(f"   Zeilen total:          {len(basel):>8}")
    for b in BETREIBER:
        print(f"     davon {b}:           {(basel['BETREIBER_ABK'] == b).sum():>8}")
    print(f"   gemessene Abfahrten:   {len(gemessen):>8}")
    print(f"   Linien:                {basel['LINIEN_TEXT'].nunique():>8}")
    print(f"   Haltestellen:          {basel['HALTESTELLEN_NAME'].nunique():>8}")
    print(f"   Linien: {', '.join(sorted(basel['LINIEN_TEXT'].dropna().unique(), key=lambda x: (len(x), x)))}")

    print("\n💾 Speicher pro Monat (Schätzung)")
    print(f"   alle Rohdaten:         {roh_mb_monat:>7.0f} MB  → 1 GB voll nach {DB_LIMIT_MB / roh_mb_monat:.1f} Monaten")
    print(f"   nur Zusammenfassung:   {zus_mb_monat:>7.0f} MB  → 1 GB voll nach {DB_LIMIT_MB / zus_mb_monat:.0f} Monaten")


if __name__ == "__main__":
    main()