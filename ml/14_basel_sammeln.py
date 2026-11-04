"""
Sammelt die Ist-Daten aller Basler Trams und Busse (BVB + BLT) als Zusammenfassung pro Stunde.

Aufruf:
  python ml/14_basel_sammeln.py       → alle fehlenden Tage (z.B. in GitHub Actions)
  python ml/14_basel_sammeln.py 1     → nur der neueste fehlende Tag (zum Testen)
"""
import importlib
import sys
import tempfile
from pathlib import Path

import pandas as pd
import requests

from datenbank import (
    verbinden, basel_tabelle_anlegen, zusammenfassen, basel_speichern,
    basel_vorhandene_tage, basel_aufraeumen,
)

sammeln = importlib.import_module("10_sammeln")   # Token + Dateiliste wiederverwenden

BETREIBER = ["BVB", "BLT"]


def tag_holen(url):
    """Tagesdatei herunterladen und nur BVB + BLT behalten."""
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
    return pd.concat(teile, ignore_index=True)


def main():
    max_tage = int(sys.argv[1]) if len(sys.argv) > 1 else None

    engine = verbinden()
    if engine is None:
        raise SystemExit("❌ DATABASE_URL nicht gefunden")
    basel_tabelle_anlegen(engine)

    verfuegbar = sammeln.tagesdateien(sammeln.lade_token())
    vorhanden = basel_vorhandene_tage(engine)
    neu = sorted(d for d in verfuegbar if d not in vorhanden)
    if max_tage:
        neu = neu[-max_tage:]                       # nur die neuesten

    print(f"📅 Verfügbar: {len(verfuegbar)} · in DB: {len(vorhanden)} · jetzt holen: {len(neu)}")

    fehler = 0
    for datum in neu:
        try:
            zeilen = basel_speichern(engine, zusammenfassen(tag_holen(verfuegbar[datum])))
            print(f"   ✅ {datum}: {zeilen} Zeilen")
        except Exception as e:
            fehler += 1
            print(f"   ❌ {datum}: {e}")

    geloescht = basel_aufraeumen(engine)
    print(f"🧹 Aufgeräumt: {geloescht} alte Zeilen gelöscht")
    print(f"🏁 Fertig. Basel-Tage in der DB: {len(basel_vorhandene_tage(engine))}")
    if fehler:
        raise SystemExit(1)


if __name__ == "__main__":
    main()