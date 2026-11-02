from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from wetter import get_weather, get_week_weather, search_locations, get_pollen, pollen_level, will_it_rain, STADT, LAT, LON
from feiertage import next_holiday
from zuege import search_stations, get_connections, FahrplanNichtErreichbar

app = FastAPI(title="Pendler API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "Welcome to the Pendler API"}


@app.get("/locations/search")
def locations_search(q: str):
    return search_locations(q)


@app.get("/weather/today")
def weather_today(lat: float = LAT, lon: float = LON, city: str = STADT):
    daten = get_weather(lat, lon)

    stunden = daten["hourly"]["time"]
    temps = daten["hourly"]["temperature_2m"]
    regen = daten["hourly"]["precipitation_probability"]

    verlauf = []
    for i in range(len(stunden)):
        verlauf.append({
            "time": stunden[i][11:16],
            "temperature": temps[i],
            "rain_probability": regen[i],
        })

    return {
        "city": city,
        "now": daten["current"]["temperature_2m"],
        "min": daten["daily"]["temperature_2m_min"][0],
        "max": daten["daily"]["temperature_2m_max"][0],
        "will_rain": will_it_rain(regen),
        "hourly": verlauf,
    }


@app.get("/weather/week")
def weather_week(lat: float = LAT, lon: float = LON, city: str = STADT):
    daten = get_week_weather(lat, lon)

    tage = daten["daily"]["time"]
    codes = daten["daily"]["weather_code"]
    maxs = daten["daily"]["temperature_2m_max"]
    mins = daten["daily"]["temperature_2m_min"]
    regen = daten["daily"]["precipitation_probability_max"]

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
        "city": city,
        "days": woche,
    }


@app.get("/pollen")
def pollen(lat: float = LAT, lon: float = LON):
    wert, art = get_pollen(lat, lon)
    key, stufe = pollen_level(wert)
    return {
        "key": key,
        "level": stufe,
        "type": art,
        "value": round(wert),
    }


@app.get("/holidays/next")
def holidays_next(canton: str = "Basel-Stadt"):
    return next_holiday(canton)


@app.get("/stations/search")
def stations_search(q: str):
    try:
        return search_stations(q)
    except FahrplanNichtErreichbar:
        raise HTTPException(status_code=503, detail="Fahrplan gerade nicht erreichbar")


@app.get("/connections")
def connections(von: str, nach: str, date: str, time: str):
    try:
        return get_connections(von, nach, date, time)
    except FahrplanNichtErreichbar:
        raise HTTPException(status_code=503, detail="Fahrplan gerade nicht erreichbar")