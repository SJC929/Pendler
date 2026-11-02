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