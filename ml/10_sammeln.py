"""
Sammelt die neuen Ist-Daten für Bus 48 (BVB).

1. Fragt bei opentransportdata.swiss (CKAN) nach, welche Tagesdateien es gibt
2. Lädt nur die Tage herunter, die wir noch nicht haben
3. Behält nur Linie 48 der BVB
4. Speichert als CSV in ml/data/linie/ und (falls eingerichtet) in der Datenbank
"""
import os
import tempfile
from pathlib import Path

import pandas as pd
import requests

from datenbank import verbinden, tabelle_anlegen, speichern

ML = Path(__file__).resolve().parent
ZIEL = ML / "data" / "linie"

CKAN_URL = "https://api.opentransportdata.swiss/ckan-api/package_show"
DATENSATZ = "ist-daten-v2"

SPALTEN = [
    "BETRIEBSTAG", "FAHRT_BEZEICHNER", "BETREIBER_ABK", "PRODUKT_ID", "LINIEN_TEXT",
    "FAELLT_AUS_TF", "HALTESTELLEN_NAME", "ANKUNFTSZEIT", "AN_PROGNOSE",
    "AN_PROGNOSE_STATUS", "ABFAHRTSZEIT", "AB_PROGNOSE", "AB_PROGNOSE_STATUS",
]


def lade_token():
    """Token aus der Umgebung (GitHub Actions) oder aus der Datei .env (lokal) lesen."""
    if os.environ.get("OTD_TOKEN"):
        return os.environ["OTD_TOKEN"].strip()
    env_datei = ML.parent / ".env"
    if env_datei.exists():
        for zeile in env_datei.read_text(encoding="utf-8-sig").splitlines():
            if "=" in zeile and zeile.split("=", 1)[0].strip().upper() == "OTD_TOKEN":
                return zeile.split("=", 1)[1].strip()
    raise RuntimeError("OTD_TOKEN nicht gefunden – steht er in der Datei .env?")


def tagesdateien(token):
    """Alle verfügbaren Tage mit Download-Link, z.B. {"2026-11-02": "https://..."}."""
    antwort = requests.get(
        CKAN_URL, params={"id": DATENSATZ}, headers={"Authorization": token}, timeout=60
    )
    antwort.raise_for_status()

    dateien = {}
    for r in antwort.json()["result"]["resources"]:
        url = r.get("url", "")
        name = url.rsplit("/", 1)[-1]          # "2026-11-02_istdaten.csv"
        if name.endswith("_istdaten.csv"):
            dateien[name[:10]] = url
    return dict(sorted(dateien.items()))


def tag_holen(datum, url, engine):
    """Eine Tagesdatei herunterladen, Bus 48 herausfiltern, speichern."""
    teile = []
    with tempfile.TemporaryDirectory() as ordner:
        pfad = Path(ordner) / "tag.csv"

        # 1. Herunterladen in eine temporäre Datei (Stück für Stück, spart Arbeitsspeicher)
        with requests.get(url, stream=True, timeout=300) as antwort:
            antwort.raise_for_status()
            with open(pfad, "wb") as datei:
                for stueck in antwort.iter_content(1024 * 1024):
                    datei.write(stueck)

        # 2. In Häppchen lesen und nur Bus 48 der BVB behalten
        for chunk in pd.read_csv(pfad, sep=";", dtype=str, usecols=SPALTEN, chunksize=500_000):
            teile.append(chunk[(chunk["LINIEN_TEXT"] == "48") & (chunk["BETREIBER_ABK"] == "BVB")])

    linie = pd.concat(teile, ignore_index=True)
    linie.to_csv(ZIEL / f"{datum}_linie_48.csv", index=False)
    if engine is not None:
        speichern(engine, linie)
    return len(linie)


def main():
    ZIEL.mkdir(parents=True, exist_ok=True)
    token = lade_token()

    engine = verbinden()
    if engine is not None:
        tabelle_anlegen(engine)
        print("🗄️ Datenbank verbunden")
    else:
        print("ℹ️ Keine DATABASE_URL – speichere nur als CSV")

    verfuegbar = tagesdateien(token)
    vorhanden = {p.name[:10] for p in ZIEL.glob("*_linie_48.csv")}
    neu = [d for d in verfuegbar if d not in vorhanden]

    print(f"📅 Verfügbar: {len(verfuegbar)} Tage · schon gespeichert: {len(vorhanden)} · neu: {len(neu)}")

    fehler = 0
    for datum in neu:
        try:
            zeilen = tag_holen(datum, verfuegbar[datum], engine)
            print(f"   ✅ {datum}: {zeilen} Zeilen")
        except Exception as e:
            fehler += 1
            print(f"   ❌ {datum}: {e}")

    print(f"🏁 Fertig. Jetzt {len(vorhanden) + len(neu) - fehler} Tage für Linie 48 (BVB).")
    if fehler:
        raise SystemExit(1)   # GitHub Actions soll merken, dass etwas schiefging


if __name__ == "__main__":
    main()