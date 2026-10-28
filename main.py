from fastapi import FastAPI
from wetter import get_weather, get_week_weather, will_it_rain, STADT, LAT, LON
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Pendler API")


@app.get("/")
def home():
    return {"message": "Welcome to the Pendler API"}


@app.get("/weather/today")
def weather_today():
    daten = get_weather(LAT, LON)

    stunden = daten["hourly"]["time"]
    temps = daten["hourly"]["temperature_2m"]
    regen = daten["hourly"]["precipitation_probability"]

    # Stundenverlauf als Liste aufbauen
    verlauf = []
    for i in range(len(stunden)):
        verlauf.append({
            "time": stunden[i][11:16],
            "temperature": temps[i],
            "rain_probability": regen[i],
        })

    return {
        "city": STADT,
        "now": daten["current"]["temperature_2m"],
        "min": daten["daily"]["temperature_2m_min"][0],
        "max": daten["daily"]["temperature_2m_max"][0],
        "will_rain": will_it_rain(regen),
        "hourly": verlauf,
    }


@app.get("/weather/week")
def weather_week():
    daten = get_week_weather(LAT, LON)

    tage = daten["daily"]["time"]
    codes = daten["daily"]["weather_code"]
    maxs = daten["daily"]["temperature_2m_max"]
    mins = daten["daily"]["temperature_2m_min"]
    regen = daten["daily"]["precipitation_probability_max"]

    # Für jeden Tag eine «Kachel» bauen
    woche = []
    for i in range(len(tage)):
        woche.append({
            "date": tage[i],
            "weather_code": codes[i],
            "max": maxs[i],
            "min": mins[i],
            "rain_probability": regen[i],
        })

    return {
        "city": STADT,
        "days": woche,
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)