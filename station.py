"""Verspätungsprognose pro Haltestelle für ganz Basel (liest die Tabelle basel_prognose)."""
import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg


class DatenbankFehlt(Exception):
    """Keine DATABASE_URL oder die Datenbank antwortet nicht."""


def lade_url():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        env_datei = Path(__file__).resolve().parent / ".env"
        if env_datei.exists():
            for zeile in env_datei.read_text(encoding="utf-8-sig").splitlines():
                if "=" in zeile and zeile.split("=", 1)[0].strip().upper() == "DATABASE_URL":
                    url = zeile.split("=", 1)[1].strip().strip('"').strip("'")
    if not url:
        raise DatenbankFehlt()
    return url


def abfrage(sql, parameter):
    try:
        # prepare_threshold=None: funktioniert auch mit dem Neon-Pooler auf Vercel
        with psycopg.connect(lade_url(), prepare_threshold=None, connect_timeout=10) as conn:
            return conn.execute(sql, parameter).fetchall()
    except psycopg.Error:
        raise DatenbankFehlt() from None


def haltestellen_suchen(text):
    zeilen = abfrage(
        "SELECT DISTINCT haltestelle FROM basel_prognose WHERE haltestelle ILIKE %s ORDER BY haltestelle LIMIT 10",
        (f"%{text}%",),
    )
    return [z[0] for z in zeilen]


def gruppieren(zeilen):
    """Zeilen aus der DB → eine Gruppe pro Linie + Ziel, mit den Stunden darin."""
    gruppen = {}
    for betreiber, linie, ziel, stunde, risiko in zeilen:
        g = gruppen.setdefault(
            (betreiber, linie, ziel),
            {"betreiber": betreiber, "linie": linie, "ziel": ziel, "stunden": []},
        )
        g["stunden"].append({"stunde": stunde, "risiko": risiko})
    # Linie 6 vor Linie 11 vor Linie 36 (nach Länge, dann alphabetisch)
    return sorted(gruppen.values(), key=lambda g: (len(g["linie"]), g["linie"], g["ziel"]))


def station_prognose(haltestelle, datum=None):
    tag = date.fromisoformat(datum) if datum else datetime.now(ZoneInfo("Europe/Zurich")).date()
    zeilen = abfrage(
        """SELECT betreiber, linie, ziel, stunde, risiko
           FROM basel_prognose
           WHERE haltestelle = %s AND datum = %s
           ORDER BY linie, ziel, stunde""",
        (haltestelle, tag),
    )
    return {"haltestelle": haltestelle, "datum": tag.isoformat(), "linien": gruppieren(zeilen)}