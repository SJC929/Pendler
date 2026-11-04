"""Verbindung zur PostgreSQL-Datenbank (Neon) und Speichern der Ist-Daten."""
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

ML = Path(__file__).resolve().parent

TABELLE = """
CREATE TABLE IF NOT EXISTS fahrten (
    betriebstag     DATE NOT NULL,
    fahrt           TEXT NOT NULL,
    betreiber       TEXT,
    produkt         TEXT,
    linie           TEXT,
    faellt_aus      BOOLEAN,
    haltestelle     TEXT,
    ankunft_plan    TIMESTAMP,
    ankunft_ist     TIMESTAMP,
    ankunft_status  TEXT,
    abfahrt_plan    TIMESTAMP,
    abfahrt_ist     TIMESTAMP,
    abfahrt_status  TEXT
)
"""
INDIZES = [
    "CREATE INDEX IF NOT EXISTS fahrten_tag ON fahrten (betriebstag)",
    "CREATE INDEX IF NOT EXISTS fahrten_linie ON fahrten (betreiber, linie)",
]


def lade_url():
    """DATABASE_URL aus der Umgebung (GitHub) oder aus der Datei .env (lokal)."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        env_datei = ML.parent / ".env"
        if env_datei.exists():
            for zeile in env_datei.read_text(encoding="utf-8-sig").splitlines():
                if "=" in zeile and zeile.split("=", 1)[0].strip().upper() == "DATABASE_URL":
                    url = zeile.split("=", 1)[1].strip().strip('"').strip("'")
    if not url:
        return None
    # SQLAlchemy soll den Treiber psycopg (Version 3) verwenden
    for alt in ("postgresql://", "postgres://"):
        if url.startswith(alt):
            url = "postgresql+psycopg://" + url[len(alt):]
    return url


def verbinden():
    """Verbindung zur Datenbank, oder None, wenn keine DATABASE_URL gesetzt ist."""
    url = lade_url()
    return create_engine(url, pool_pre_ping=True) if url else None


def tabelle_anlegen(engine):
    with engine.begin() as conn:
        conn.execute(text(TABELLE))
        for befehl in INDIZES:
            conn.execute(text(befehl))


def zeit(spalte):
    return pd.to_datetime(spalte, format="mixed", dayfirst=True, errors="coerce")


def aufbereiten(roh):
    """Spalten aus der CSV-Datei → Spalten der Datenbank-Tabelle."""
    return pd.DataFrame({
        "betriebstag": pd.to_datetime(roh["BETRIEBSTAG"], format="mixed", dayfirst=True).dt.date,
        "fahrt": roh["FAHRT_BEZEICHNER"],
        "betreiber": roh["BETREIBER_ABK"],
        "produkt": roh["PRODUKT_ID"],
        "linie": roh["LINIEN_TEXT"],
        "faellt_aus": roh["FAELLT_AUS_TF"].astype(str).str.lower().eq("true"),
        "haltestelle": roh["HALTESTELLEN_NAME"],
        "ankunft_plan": zeit(roh["ANKUNFTSZEIT"]),
        "ankunft_ist": zeit(roh["AN_PROGNOSE"]),
        "ankunft_status": roh["AN_PROGNOSE_STATUS"],
        "abfahrt_plan": zeit(roh["ABFAHRTSZEIT"]),
        "abfahrt_ist": zeit(roh["AB_PROGNOSE"]),
        "abfahrt_status": roh["AB_PROGNOSE_STATUS"],
    })


def speichern(engine, roh):
    """Speichert Ist-Daten. Gibt es den Tag + die Linie schon, wird ersetzt (kein Doppeltes)."""
    df = aufbereiten(roh)
    kombis = df[["betriebstag", "betreiber", "linie"]].drop_duplicates()

    with engine.begin() as conn:
        for k in kombis.itertuples():
            conn.execute(
                text("DELETE FROM fahrten WHERE betriebstag = :t AND betreiber = :b AND linie = :l"),
                {"t": k.betriebstag, "b": k.betreiber, "l": k.linie},
            )
        df.to_sql("fahrten", conn, if_exists="append", index=False, method="multi", chunksize=1000)
    return len(df)


def anzahl(engine):
    with engine.connect() as conn:
        zeilen = conn.execute(text("SELECT COUNT(*) FROM fahrten")).scalar()
        tage = conn.execute(text("SELECT COUNT(DISTINCT betriebstag) FROM fahrten")).scalar()
    return zeilen, tage

# ===== Ganz Basel: Zusammenfassung pro Stunde =====

BASEL_TABELLE = """
CREATE TABLE IF NOT EXISTS basel_stunden (
    datum               DATE NOT NULL,
    betreiber           TEXT NOT NULL,
    linie               TEXT NOT NULL,
    haltestelle         TEXT NOT NULL,
    ziel                TEXT NOT NULL,
    stunde              SMALLINT NOT NULL,
    abfahrten           INTEGER NOT NULL,
    zu_spaet            INTEGER NOT NULL,
    verspaetung_mittel  REAL,
    PRIMARY KEY (datum, betreiber, linie, haltestelle, ziel, stunde)
)
"""


def basel_tabelle_anlegen(engine):
    with engine.begin() as conn:
        conn.execute(text(BASEL_TABELLE))


def zusammenfassen(roh, schwelle_min=3):
    """Rohdaten eines Tages → eine Zeile pro Linie, Haltestelle, Ziel und Stunde."""
    df = roh.copy()
    df["plan"] = zeit(df["ABFAHRTSZEIT"])
    df["ist"] = zeit(df["AB_PROGNOSE"])
    df["fahrt"] = df["BETRIEBSTAG"] + "_" + df["FAHRT_BEZEICHNER"]

    # Ziel jeder Fahrt = letzte Haltestelle
    df["reihenfolge"] = df["plan"].fillna(zeit(df["ANKUNFTSZEIT"]))
    ziel = df.sort_values("reihenfolge").groupby("fahrt")["HALTESTELLEN_NAME"].last()
    df["ziel"] = df["fahrt"].map(ziel)

    # Nur echt gemessene Abfahrten, Messfehler weglassen
    df = df[(df["AB_PROGNOSE_STATUS"] == "REAL") & df["plan"].notna() & df["ist"].notna()].copy()
    df["verspaetung"] = (df["ist"] - df["plan"]).dt.total_seconds() / 60
    df = df[df["verspaetung"].between(-2, 30)]

    df["datum"] = pd.to_datetime(df["BETRIEBSTAG"], format="mixed", dayfirst=True).dt.date
    df["stunde"] = df["plan"].dt.hour
    df["spaet"] = (df["verspaetung"] > schwelle_min).astype(int)

    zusammen = (
        df.groupby(["datum", "BETREIBER_ABK", "LINIEN_TEXT", "HALTESTELLEN_NAME", "ziel", "stunde"])
        .agg(abfahrten=("spaet", "size"), zu_spaet=("spaet", "sum"), verspaetung_mittel=("verspaetung", "mean"))
        .reset_index()
        .rename(columns={"BETREIBER_ABK": "betreiber", "LINIEN_TEXT": "linie", "HALTESTELLEN_NAME": "haltestelle"})
    )
    zusammen["verspaetung_mittel"] = zusammen["verspaetung_mittel"].round(2)
    return zusammen


def basel_speichern(engine, zusammen):
    """Speichert einen Tag. Gibt es den Tag schon, wird er ersetzt."""
    with engine.begin() as conn:
        for datum in zusammen["datum"].unique():
            conn.execute(text("DELETE FROM basel_stunden WHERE datum = :d"), {"d": datum})
        zusammen.to_sql("basel_stunden", conn, if_exists="append", index=False, method="multi", chunksize=1000)
    return len(zusammen)


def basel_vorhandene_tage(engine):
    with engine.connect() as conn:
        zeilen = conn.execute(text("SELECT DISTINCT datum FROM basel_stunden")).fetchall()
    return {z[0].isoformat() for z in zeilen}


def basel_aufraeumen(engine, tage_behalten=120):
    """Löscht alles, was älter als 120 Tage ist (damit die Gratis-DB nicht voll wird)."""
    with engine.begin() as conn:
        geloescht = conn.execute(
            text("DELETE FROM basel_stunden WHERE datum < CURRENT_DATE - :t"), {"t": tage_behalten}
        ).rowcount
    return geloescht