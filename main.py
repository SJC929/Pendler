import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from wetter import (
    get_weather, get_week_weather, search_locations, get_pollen, pollen_level,
    will_it_rain, get_commute_weather, pendel_regen, STADT, LAT, LON,
)
from feiertage import next_holiday
from zuege import search_stations, get_connections, FahrplanNichtErreichbar
from prognose import delay_prognose, haltestellen, PrognoseFehlt, HaltestelleUnbekannt

from verkehr import route_mit_verkehr, adresse_suchen, VerkehrNichtErreichbar, KeinSchluessel
from station import haltestellen_suchen, station_prognose, DatenbankFehlt

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


@app.get("/weather/commute")
def weather_commute(
    lat: float,
    lon: float,
    hin: str = Query("07:30", pattern=r"^\d{2}:\d{2}$"),
    heim: str = Query("17:00", pattern=r"^\d{2}:\d{2}$"),
):
    try:
        daten = get_commute_weather(lat, lon)
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Wetterdaten sind gerade nicht verfügbar")
    return {"hin": pendel_regen(daten, hin), "heim": pendel_regen(daten, heim)}

@app.get("/traffic/route")
def traffic_route(von_lat: float, von_lon: float, nach_lat: float, nach_lon: float):
    try:
        return route_mit_verkehr(von_lat, von_lon, nach_lat, nach_lon)
    except KeinSchluessel:
        raise HTTPException(status_code=503, detail="Verkehrsdaten sind nicht eingerichtet")
    except VerkehrNichtErreichbar:
        raise HTTPException(status_code=503, detail="Verkehrsdaten sind gerade nicht verfügbar")

@app.get("/traffic/search")
def traffic_search(q: str = Query(..., min_length=3)):
    try:
        return adresse_suchen(q)
    except KeinSchluessel:
        raise HTTPException(status_code=503, detail="Verkehrsdaten sind nicht eingerichtet")
    except VerkehrNichtErreichbar:
        raise HTTPException(status_code=503, detail="Adresssuche ist gerade nicht verfügbar")


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


@app.get("/predict/delay/stops")
def predict_delay_stops():
    try:
        return haltestellen()
    except PrognoseFehlt:
        raise HTTPException(status_code=503, detail="Prognose ist gerade nicht verfügbar")


@app.get("/predict/delay")
def predict_delay(haltestelle: str, richtung: str, datum: str | None = None):
    try:
        return delay_prognose(haltestelle, richtung, datum)
    except PrognoseFehlt:
        raise HTTPException(status_code=503, detail="Prognose ist gerade nicht verfügbar")
    except HaltestelleUnbekannt:
        raise HTTPException(status_code=404, detail="Keine Prognose für diese Haltestelle/Richtung")


@app.get("/predict/station/search")
def predict_station_search(q: str = Query(..., min_length=2)):
    try:
        return haltestellen_suchen(q)
    except DatenbankFehlt:
        raise HTTPException(status_code=503, detail="Prognose ist gerade nicht verfügbar")


@app.get("/predict/station")
def predict_station(haltestelle: str, datum: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$")):
    try:
        return station_prognose(haltestelle, datum)
    except DatenbankFehlt:
        raise HTTPException(status_code=503, detail="Prognose ist gerade nicht verfügbar")