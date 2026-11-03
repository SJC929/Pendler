"""Live-Verkehr für eine Autofahrt mit der TomTom Routing API."""
import math
import os
from pathlib import Path

import requests

from urllib.parse import quote

ROUTING_URL = "https://api.tomtom.com/routing/1/calculateRoute/{von}:{nach}/json"
SUCH_URL = "https://api.tomtom.com/search/2/search/{text}.json"
ZEITLIMIT = 10

ARTEN = {"JAM": "Stau", "ROAD_WORK": "Baustelle", "ROAD_CLOSURE": "Sperrung"}


class VerkehrNichtErreichbar(Exception):
    """TomTom antwortet nicht oder mit einem Fehler."""


class KeinSchluessel(Exception):
    """TOMTOM_KEY ist weder bei Vercel noch in der Datei .env gesetzt."""


def lade_schluessel():
    """Key aus der Umgebung (Vercel) oder aus der Datei .env (lokal) lesen."""
    if os.environ.get("TOMTOM_KEY"):
        return os.environ["TOMTOM_KEY"]
    env_datei = Path(__file__).resolve().parent / ".env"
    if env_datei.exists():
        for zeile in env_datei.read_text(encoding="utf-8").splitlines():
            if zeile.startswith("TOMTOM_KEY="):
                return zeile.split("=", 1)[1].strip()
    raise KeinSchluessel()


def abstand_km(a, b):
    """Luftlinie zwischen zwei Punkten in km (Haversine-Formel)."""
    lat1, lon1, lat2, lon2 = map(
        math.radians, (a["latitude"], a["longitude"], b["latitude"], b["longitude"])
    )
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def auswerten(daten):
    """Macht aus der TomTom-Antwort eine einfache Übersicht."""
    route = daten["routes"][0]
    summe = route["summary"]

    # Für jeden Punkt der Route: wie viele km seit dem Start?
    punkte = [p for leg in route["legs"] for p in leg["points"]]
    km_bis = [0.0]
    for i in range(1, len(punkte)):
        km_bis.append(km_bis[-1] + abstand_km(punkte[i - 1], punkte[i]))

    staus = []
    for abschnitt in route.get("sections", []):
        if abschnitt.get("sectionType") != "TRAFFIC":
            continue
        verzoegerung = abschnitt.get("delayInSeconds", 0)
        if verzoegerung < 60:                      # unter 1 Minute ignorieren
            continue
        start = min(abschnitt.get("startPointIndex", 0), len(km_bis) - 1)
        staus.append({
            "art": ARTEN.get(abschnitt.get("simpleCategory"), "Behinderung"),
            "verzoegerung_min": round(verzoegerung / 60),
            "tempo_kmh": abschnitt.get("effectiveSpeedInKmh"),
            "bei_km": round(km_bis[start]),
        })

    return {
        "dauer_min": round(summe["travelTimeInSeconds"] / 60),
        "ohne_stau_min": round(summe.get("noTrafficTravelTimeInSeconds", summe["travelTimeInSeconds"]) / 60),
        "stau_min": round(summe.get("trafficDelayInSeconds", 0) / 60),
        "distanz_km": round(summe["lengthInMeters"] / 1000, 1),
        "ankunft": summe["arrivalTime"][11:16],
        "staus": staus,
    }


def route_mit_verkehr(von_lat, von_lon, nach_lat, nach_lon):
    url = ROUTING_URL.format(von=f"{von_lat},{von_lon}", nach=f"{nach_lat},{nach_lon}")
    params = {
        "key": lade_schluessel(),
        "traffic": "true",
        "travelMode": "car",
        "routeType": "fastest",
        "computeTravelTimeFor": "all",
        "sectionType": "traffic",
    }
    try:
        antwort = requests.get(url, params=params, timeout=ZEITLIMIT)
        antwort.raise_for_status()
    except requests.RequestException:
        # "from None": die Fehlermeldung enthält die URL mit dem Key → nicht weitergeben
        raise VerkehrNichtErreichbar() from None
    return auswerten(antwort.json())

def treffer_auswerten(treffer):
    """Ein Suchtreffer von TomTom → {name, lat, lon}."""
    adresse = treffer.get("address", {}).get("freeformAddress", "")
    ort_name = treffer.get("poi", {}).get("name")          # z.B. «Messe Basel»
    return {
        "name": f"{ort_name}, {adresse}" if ort_name else adresse,
        "lat": treffer["position"]["lat"],
        "lon": treffer["position"]["lon"],
    }


def adresse_suchen(text):
    """Sucht Adressen und Orte in der Schweiz, während man tippt."""
    params = {
        "key": lade_schluessel(),
        "countrySet": "CH",
        "limit": 6,
        "language": "de-DE",
        "typeahead": "true",          # auch halbe Wörter finden («Bahnhofst»)
    }
    try:
        antwort = requests.get(SUCH_URL.format(text=quote(text, safe="")), params=params, timeout=ZEITLIMIT)
        antwort.raise_for_status()
    except requests.RequestException:
        raise VerkehrNichtErreichbar() from None
    return [treffer_auswerten(t) for t in antwort.json().get("results", [])]