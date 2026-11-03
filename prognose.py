import json
from pathlib import Path

DATEI = Path(__file__).resolve().parent / "prognosen" / "bus48.json"


class PrognoseFehlt(Exception):
    """Die Prognose-Datei gibt es nicht oder sie ist kaputt."""


class HaltestelleUnbekannt(Exception):
    """Für diese Haltestelle/Richtung gibt es keine Prognose."""


def lade_prognose():
    try:
        return json.loads(DATEI.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as fehler:
        raise PrognoseFehlt(str(fehler)) from fehler


def haltestellen():
    """Alle Haltestellen pro Richtung, z.B. für ein Dropdown im Frontend."""
    daten = lade_prognose()
    richtungen = {}
    for p in daten["prognosen"]:
        richtungen.setdefault(p["richtung"], set()).add(p["haltestelle"])
    return {
        "linie": daten["linie"],
        "richtungen": {r: sorted(h) for r, h in richtungen.items()},
    }


def delay_prognose(haltestelle, richtung, datum=None):
    daten = lade_prognose()
    stunden = [
        {"datum": p["datum"], "stunde": p["stunde"], "risiko": p["risiko"]}
        for p in daten["prognosen"]
        if p["haltestelle"] == haltestelle
        and p["richtung"] == richtung
        and (datum is None or p["datum"] == datum)
    ]
    if not stunden:
        raise HaltestelleUnbekannt(f"{haltestelle} ({richtung})")

    return {
        "linie": daten["linie"],
        "betreiber": daten["betreiber"],
        "erstellt": daten["erstellt"],
        "schwelle_min": daten["schwelle_min"],
        "haltestelle": haltestelle,
        "richtung": richtung,
        "stunden": stunden,
    }