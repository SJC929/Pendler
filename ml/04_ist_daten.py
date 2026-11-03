"""Filtert eine Linie aus heruntergeladenen Ist-Daten-Dateien.

Vorher die Tagesdatei von Hand herunterladen:
https://data.opentransportdata.swiss/dataset/ist-daten-v2
und nach ml/data/raw/ legen (z. B. 2026-11-01_IstDaten.csv).
"""
import csv
import sys
from pathlib import Path

import pandas as pd

LINIE = "48"   # die Linie, die uns interessiert
BETREIBER = "BVB"   # Basler Verkehrs-Betriebe (48 gibt es auch in Genf, Lausanne, Bern)
ORDNER = Path(__file__).parent / "data"
ROH_ORDNER = ORDNER / "raw"
ZIEL_ORDNER = ORDNER / "linie"

SPALTEN = [
    "BETRIEBSTAG", "FAHRT_BEZEICHNER", "BETREIBER_ABK", "PRODUKT_ID",
    "LINIEN_TEXT", "FAELLT_AUS_TF", "HALTESTELLEN_NAME",
    "ANKUNFTSZEIT", "AN_PROGNOSE", "AN_PROGNOSE_STATUS",
    "ABFAHRTSZEIT", "AB_PROGNOSE", "AB_PROGNOSE_STATUS",
]


def finde_dateien(datum=None):
    """Sucht Ist-Daten-Dateien in ml/data/raw/ (Gross-/Kleinschreibung egal)."""
    alle = [p for p in ROH_ORDNER.glob("*.csv") if "istdaten" in p.name.lower()]
    if datum:
        alle = [p for p in alle if p.name.startswith(datum)]
    return sorted(alle)


def linie_herausfiltern(pfad):
    """Liest die riesige Datei in Stücken und behält nur unsere Linie."""
    with open(pfad, encoding="utf-8", errors="replace") as f:
        trennzeichen = csv.Sniffer().sniff(f.readline()).delimiter

    kopf = pd.read_csv(pfad, sep=trennzeichen, nrows=0).columns
    vorhanden = [s for s in SPALTEN if s in kopf]
    fehlend = [s for s in SPALTEN if s not in kopf]
    if fehlend:
        print("  ⚠️ Diese Spalten fehlen:", fehlend)
        print("  Vorhanden sind:", list(kopf))

    treffer = []
    for stueck in pd.read_csv(pfad, sep=trennzeichen, usecols=vorhanden,
                              dtype=str, chunksize=500_000):
        passt = (stueck["LINIEN_TEXT"] == LINIE) & (stueck["BETREIBER_ABK"] == BETREIBER)
        treffer.append(stueck[passt])
        print("·", end="", flush=True)
    print()
    return pd.concat(treffer)


def datei_verarbeiten(pfad):
    datum = pfad.name[:10]   # "2026-11-01_IstDaten.csv" → "2026-11-01"
    print(f"✂️  {pfad.name}: filtere Linie {LINIE} …")
    linie = linie_herausfiltern(pfad)

    ZIEL_ORDNER.mkdir(parents=True, exist_ok=True)
    ziel = ZIEL_ORDNER / f"{datum}_linie_{LINIE}.csv"
    linie.to_csv(ziel, index=False)
    print(f"💾 {len(linie):,} Zeilen gespeichert in {ziel}")
    return linie


if __name__ == "__main__":
    datum = sys.argv[1] if len(sys.argv) > 1 else None
    dateien = finde_dateien(datum)

    if not dateien:
        print("❌ Keine Ist-Daten-Datei gefunden in", ROH_ORDNER)
        print("   Bitte zuerst herunterladen und dort ablegen.")
        sys.exit(1)

    for pfad in dateien:
        linie = datei_verarbeiten(pfad)

    # Kontrolle (letzte Datei): Welche Linie 48 haben wir erwischt?
    print("\nBetreiber:\n", linie["BETREIBER_ABK"].value_counts())
    print("\nVerkehrsmittel:\n", linie["PRODUKT_ID"].value_counts())
    print("\nHäufigste Haltestellen:\n", linie["HALTESTELLEN_NAME"].value_counts().head(10))
    print("\nTipp: Die grosse Rohdatei in ml/data/raw/ kannst du jetzt löschen.")