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