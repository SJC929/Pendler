"""Einmalig: alle gesammelten CSV-Dateien in die Datenbank laden."""
from pathlib import Path

import pandas as pd

from datenbank import verbinden, tabelle_anlegen, speichern, anzahl

LINIE = Path(__file__).resolve().parent / "data" / "linie"


def main():
    engine = verbinden()
    if engine is None:
        raise SystemExit("❌ DATABASE_URL nicht gefunden – steht sie in der Datei .env?")

    tabelle_anlegen(engine)
    print("✅ Tabelle «fahrten» bereit")

    dateien = sorted(LINIE.glob("*_linie_48.csv"))
    for i, pfad in enumerate(dateien, 1):
        zeilen = speichern(engine, pd.read_csv(pfad, dtype=str))
        print(f"   {i:3d}/{len(dateien)}  {pfad.name}: {zeilen} Zeilen")

    zeilen, tage = anzahl(engine)
    print(f"🏁 In der Datenbank: {zeilen} Zeilen, {tage} Tage")


if __name__ == "__main__":
    main()