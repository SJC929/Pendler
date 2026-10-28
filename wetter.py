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
        "timezone": "Europe/Zurich",
        "forecast_days": 1,
    }
    antwort = requests.get(url, params=params)
    return antwort.json()


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
daten = get_weather(LAT, LON)
show_weather(STADT, daten)