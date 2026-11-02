from datetime import datetime
from zoneinfo import ZoneInfo
import requests

BASIS_URL = "https://transport.opendata.ch/v1"
ZEITZONE = ZoneInfo("Europe/Zurich")

# Kategorie aus dem Fahrplan → Verkehrsmittel
TRAM = {"T", "NFT", "TRAM"}
BUS = {"B", "BUS", "NFB", "KB", "EXB", "BP"}
SCHIFF = {"BAT", "BAV", "FAE"}


def verkehrsmittel(kategorie):
    """'T' → 'tram', 'B' → 'bus', 'IR' → 'train' usw."""
    k = (kategorie or "").upper()
    if k in TRAM:
        return "tram"
    if k in BUS:
        return "bus"
    if k in SCHIFF:
        return "ship"
    return "train"


def search_stations(name):
    """Sucht Bahnhöfe/Haltestellen nach Namen."""
    params = {"query": name, "type": "station"}
    antwort = requests.get(f"{BASIS_URL}/locations", params=params)
    daten = antwort.json()

    stationen = []
    for station in daten.get("stations", []):
        if station.get("name") and station.get("id"):
            stationen.append({"id": station["id"], "name": station["name"]})
    return stationen[:8]


def dauer_schoen(dauer):
    """'00d01:05:00' → '1h 05min'"""
    tage, rest = dauer.split("d")
    stunden, minuten, _ = rest.split(":")
    stunden = int(tage) * 24 + int(stunden)
    if stunden == 0:
        return f"{int(minuten)} min"
    return f"{stunden}h {minuten}min"


def erstes_fahrzeug(verbindung):
    """Sucht das erste Fahrzeug der Verbindung (Fusswege überspringen)."""
    for abschnitt in verbindung.get("sections", []):
        fahrt = abschnitt.get("journey")
        if fahrt:
            return fahrt.get("category"), fahrt.get("number")
    return None, None


def get_connections(von, nach, datum, zeit, stunden=3):
    """Verbindungen ab einer Uhrzeit, für die nächsten 3 Stunden."""
    start = datetime.fromisoformat(f"{datum}T{zeit}").replace(tzinfo=ZEITZONE)
    start_ts = start.timestamp()
    ende_ts = start_ts + stunden * 3600

    params = {
        "from": von,
        "to": nach,
        "date": datum,
        "time": zeit,
        "limit": 16,
    }
    antwort = requests.get(f"{BASIS_URL}/connections", params=params)
    daten = antwort.json()

    verbindungen = []
    for verbindung in daten.get("connections", []):
        abfahrt = verbindung["from"]
        ts = abfahrt.get("departureTimestamp")

        # nur Abfahrten im 3-Stunden-Fenster
        if ts is None or ts < start_ts or ts > ende_ts:
            continue

        kategorie, nummer = erstes_fahrzeug(verbindung)
        art = verkehrsmittel(kategorie)

        # Linie: bei Zügen "IR 26", bei Bus/Tram nur die Nummer "48"
        if art == "train":
            linie = ", ".join(verbindung.get("products", []))
        else:
            linie = nummer or ", ".join(verbindung.get("products", []))

        prognose = abfahrt.get("prognosis") or {}
        verbindungen.append({
            "departure": abfahrt["departure"][11:16],
            "arrival": verbindung["to"]["arrival"][11:16],
            "platform": prognose.get("platform") or abfahrt.get("platform"),
            "delay": abfahrt.get("delay"),
            "duration": dauer_schoen(verbindung.get("duration") or "00d00:00:00"),
            "transfers": verbindung.get("transfers", 0),
            "type": art,
            "line": linie,
        })
    return verbindungen