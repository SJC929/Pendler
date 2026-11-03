import requests

STADT = "Basel"
LAT = 47.56
LON = 7.59


def get_weather(lat, lon):
    """Holt die Wetterdaten für einen Ort von Open-Meteo."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m",
        "hourly": "temperature_2m,precipitation_probability",
        "daily": "temperature_2m_max,temperature_2m_min",
        "timezone": "Europe/Zurich",
        "forecast_days": 1,
    }
    antwort = requests.get(url, params=params)
    return antwort.json()


def get_week_weather(lat, lon):
    """Holt die 7-Tage-Prognose für einen Ort."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "Europe/Zurich",
        "forecast_days": 7,
    }
    antwort = requests.get(url, params=params)
    return antwort.json()


def search_locations(name):
    """Sucht Orte in der Schweiz (inkl. Kanton)."""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": name,
        "count": 8,
        "language": "de",
        "countryCode": "CH",
    }
    antwort = requests.get(url, params=params)
    daten = antwort.json()

    orte = []
    for ort in daten.get("results", []):
        orte.append({
            "name": ort["name"],
            "canton": ort.get("admin1", ""),
            "lat": ort["latitude"],
            "lon": ort["longitude"],
        })
    return orte


def will_it_rain(regen):
    """True, wenn die Regenwahrscheinlichkeit irgendwann ab 50 % ist."""
    return max(regen) >= 50


def show_weather(stadt, daten):
    """Zeigt das Wetter im Terminal an."""
    jetzt = daten["current"]["temperature_2m"]
    print(f"Wetter in {stadt}: jetzt {jetzt} °C")
    print()

    stunden = daten["hourly"]["time"]
    temps = daten["hourly"]["temperature_2m"]
    regen = daten["hourly"]["precipitation_probability"]

    for i in range(len(stunden)):
        uhrzeit = stunden[i][11:16]
        print(f"{uhrzeit}   {temps[i]} °C   Regen: {regen[i]} %")

    print()
    if will_it_rain(regen):
        print("☔ Heute Regenschirm mitnehmen!")
    else:
        print("🌤️ Kein Regenschirm nötig.")


# Hauptprogramm: die Maschinen benutzen
if __name__ == "__main__":
    daten = get_weather(LAT, LON)
    show_weather(STADT, daten)

POLLEN_ARTEN = {
    "alder_pollen": "Erle",
    "birch_pollen": "Birke",
    "grass_pollen": "Gräser",
    "mugwort_pollen": "Beifuss",
    "ragweed_pollen": "Ambrosia",
}


def get_pollen(lat, lon):
    """Holt die Pollenbelastung für heute und gibt die stärkste Pollenart zurück."""
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(POLLEN_ARTEN.keys()),
        "timezone": "Europe/Zurich",
        "forecast_days": 1,
    }
    antwort = requests.get(url, params=params)
    stunden = antwort.json().get("hourly", {})

    hoechster_wert = 0
    staerkste_art = None
    for schluessel, name in POLLEN_ARTEN.items():
        werte = [w for w in stunden.get(schluessel, []) if w is not None]
        if werte and max(werte) > hoechster_wert:
            hoechster_wert = max(werte)
            staerkste_art = name

    return hoechster_wert, staerkste_art


def pollen_level(wert):
    """Übersetzt den Messwert in eine einfache Stufe (vereinfacht)."""
    if wert < 1:
        return "none", "keine"
    if wert < 20:
        return "low", "schwach"
    if wert < 100:
        return "moderate", "mässig"
    return "high", "stark"

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

SCHWEIZ = ZoneInfo("Europe/Zurich")


def get_commute_weather(lat, lon):
    """Holt stündliche Regen-Wahrscheinlichkeit und Regenmenge für heute und morgen."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation_probability,precipitation",
        "timezone": "Europe/Zurich",
        "forecast_days": 2,
    }
    antwort = requests.get(url, params=params, timeout=10)
    antwort.raise_for_status()
    return antwort.json()


def regen_stufe(wahrscheinlichkeit, menge_mm):
    """Übersetzt Wahrscheinlichkeit (%) und Menge (mm) in eine einfache Stufe."""
    if wahrscheinlichkeit >= 50 and menge_mm >= 0.2:
        return "regen"
    if wahrscheinlichkeit >= 30:
        return "vielleicht"
    return "trocken"


def pendel_regen(daten, uhrzeit, jetzt=None):
    """Regen-Stufe für die nächste Pendelzeit, z.B. uhrzeit="07:30".

    Schaut auf die Stunde der Abfahrt und die Stunde danach.
    Ist die Zeit heute schon vorbei, wird morgen genommen.
    """
    if jetzt is None:
        jetzt = datetime.now(SCHWEIZ).replace(tzinfo=None)

    stunde, minute = map(int, uhrzeit.split(":"))
    ziel = jetzt.replace(hour=stunde, minute=minute, second=0, microsecond=0)
    tag = "heute"
    if ziel + timedelta(hours=1) < jetzt:
        ziel += timedelta(days=1)
        tag = "morgen"

    start = ziel.replace(minute=0)
    fenster = {(start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(2)}

    stunden = daten["hourly"]
    wahrscheinlichkeiten, mengen = [], []
    for i, zeit in enumerate(stunden["time"]):
        if zeit in fenster:
            wahrscheinlichkeiten.append(stunden["precipitation_probability"][i] or 0)
            mengen.append(stunden["precipitation"][i] or 0)

    if not wahrscheinlichkeiten:
        return None

    w = max(wahrscheinlichkeiten)
    m = round(sum(mengen), 1)
    return {"zeit": uhrzeit, "tag": tag, "wahrscheinlichkeit": w, "menge_mm": m, "stufe": regen_stufe(w, m)}