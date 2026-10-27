import requests

# Ort an einer Stelle (später kann jeder seine Stadt wählen)
STADT = "Basel"
LAT = 47.56
LON = 7.59

# 1. Wetter-Server anrufen
url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": LAT,
    "longitude": LON,
    "current": "temperature_2m",
    "hourly": "temperature_2m,precipitation_probability",
    "timezone": "Europe/Zurich",
    "forecast_days": 1,
}
antwort = requests.get(url, params=params)
daten = antwort.json()

# 2. Aktuelle Temperatur
jetzt = daten["current"]["temperature_2m"]
print(f"Wetter in {STADT}: jetzt {jetzt} °C")
print()

# 3. Verlauf über den Tag
stunden = daten["hourly"]["time"]
temps = daten["hourly"]["temperature_2m"]
regen = daten["hourly"]["precipitation_probability"]

for i in range(len(stunden)):
    uhrzeit = stunden[i][11:16]
    print(f"{uhrzeit}   {temps[i]} °C   Regen: {regen[i]} %")

# 4. Regnet es heute?
print()
if max(regen) >= 50:
    print("☔ Heute Regenschirm mitnehmen!")
else:
    print("🌤️ Kein Regenschirm nötig.")