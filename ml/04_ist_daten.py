"""Filtert eine Linie aus heruntergeladenen Ist-Daten (CSV oder Monats-ZIP).

Vorher herunterladen und nach ml/data/raw/ legen:
- einzelne Tage:  https://data.opentransportdata.swiss/dataset/ist-daten-v2
- ganze Monate:   https://archive.opentransportdata.swiss/  (ZIP)
"""
import csv
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd

LINIE = "48"        # die Linie, die uns interessiert
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


def ziel_pfad(datum):
    return ZIEL_ORDNER / f"{datum}_linie_{LINIE}.csv"


def filtern(oeffnen, name):
    """Liest eine Tagesdatei in Stücken und behält nur unsere Linie.

    `oeffnen` ist eine Funktion, die die Datei (neu) öffnet. So funktioniert
    derselbe Code für normale Dateien und für Dateien in einem ZIP.
    """
    with oeffnen() as f:
        erste_zeile = io.TextIOWrapper(f, encoding="utf-8", errors="replace").readline()
    trennzeichen = csv.Sniffer().sniff(erste_zeile).delimiter

    with oeffnen() as f:
        kopf = pd.read_csv(f, sep=trennzeichen, nrows=0).columns
    vorhanden = [s for s in SPALTEN if s in kopf]
    fehlend = [s for s in SPALTEN if s not in kopf]
    if fehlend:
        print(f"  ⚠️ {name}: Diese Spalten fehlen:", fehlend)

    treffer = []
    with oeffnen() as f:
        for stueck in pd.read_csv(f, sep=trennzeichen, usecols=vorhanden,
                                  dtype=str, chunksize=500_000):
            passt = (stueck["LINIEN_TEXT"] == LINIE) & (stueck["BETREIBER_ABK"] == BETREIBER)
            treffer.append(stueck[passt])
            print("·", end="", flush=True)
    print()
    return pd.concat(treffer)


def speichern(datum, linie):
    ZIEL_ORDNER.mkdir(parents=True, exist_ok=True)
    linie.to_csv(ziel_pfad(datum), index=False)
    print(f"  💾 {datum}: {len(linie):,} Zeilen")


def csv_verarbeiten(pfad):
    datum = pfad.name[:10]
    if ziel_pfad(datum).exists():
        print(f"⏭️  {datum} schon vorhanden, übersprungen")
        return
    print(f"✂️  {pfad.name}")
    speichern(datum, filtern(lambda: open(pfad, "rb"), pfad.name))


def zip_verarbeiten(pfad):
    print(f"📦 {pfad.name}")
    with zipfile.ZipFile(pfad) as archiv:
        tagesdateien = sorted(n for n in archiv.namelist()
                              if n.lower().endswith(".csv") and "istdaten" in n.lower())
        print(f"   {len(tagesdateien)} Tagesdateien im ZIP")
        for name in tagesdateien:
            datum = Path(name).name[:10]
            if ziel_pfad(datum).exists():
                print(f"⏭️  {datum} schon vorhanden, übersprungen")
                continue
            print(f"✂️  {Path(name).name}")
            speichern(datum, filtern(lambda n=name: archiv.open(n), name))


if __name__ == "__main__":
    dateien = sorted(p for p in ROH_ORDNER.iterdir()
                     if p.suffix.lower() in (".csv", ".zip") and "istdaten" in p.name.lower()
                     or p.suffix.lower() == ".zip")

    if not dateien:
        print("❌ Keine Ist-Daten (CSV oder ZIP) gefunden in", ROH_ORDNER)
        sys.exit(1)

    for pfad in dateien:
        if pfad.suffix.lower() == ".zip":
            zip_verarbeiten(pfad)
        else:
            csv_verarbeiten(pfad)

    anzahl = len(list(ZIEL_ORDNER.glob(f"*_linie_{LINIE}.csv")))
    print(f"\n✅ Fertig. {anzahl} Tage für Linie {LINIE} ({BETREIBER}) in {ZIEL_ORDNER}")