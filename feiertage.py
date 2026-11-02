from datetime import date, timedelta
import requests

# Kantonsname (wie ihn die Ortssuche liefert) → Kürzel
KANTONE = {
    "Zürich": "ZH", "Zurich": "ZH",
    "Bern": "BE", "Berne": "BE",
    "Luzern": "LU", "Lucerne": "LU",
    "Uri": "UR",
    "Schwyz": "SZ",
    "Obwalden": "OW",
    "Nidwalden": "NW",
    "Glarus": "GL",
    "Zug": "ZG",
    "Freiburg": "FR", "Fribourg": "FR",
    "Solothurn": "SO",
    "Basel-Stadt": "BS", "Basel-City": "BS",
    "Basel-Landschaft": "BL", "Basel-Land": "BL",
    "Schaffhausen": "SH",
    "Appenzell Ausserrhoden": "AR",
    "Appenzell Innerrhoden": "AI",
    "St. Gallen": "SG", "Sankt Gallen": "SG",
    "Graubünden": "GR", "Grisons": "GR",
    "Aargau": "AG",
    "Thurgau": "TG",
    "Tessin": "TI", "Ticino": "TI",
    "Waadt": "VD", "Vaud": "VD",
    "Wallis": "VS", "Valais": "VS",
    "Neuenburg": "NE", "Neuchâtel": "NE",
    "Genf": "GE", "Genève": "GE", "Geneva": "GE",
    "Jura": "JU",
}


def deutscher_name(feiertag):
    """Sucht den deutschen Namen des Feiertags."""
    for eintrag in feiertag.get("name", []):
        if eintrag.get("language") == "DE":
            return eintrag.get("text")
    return "Feiertag"


def gilt_im_kanton(feiertag, kuerzel):
    """True, wenn der Feiertag schweizweit oder im Kanton gilt."""
    if feiertag.get("nationwide"):
        return True
    if kuerzel is None:
        return False
    for region in feiertag.get("subdivisions", []):
        if region.get("code") == f"CH-{kuerzel}":
            return True
    return False


def next_holiday(kanton_name):
    """Findet den nächsten Feiertag für einen Kanton."""
    # «Kanton Basel-Stadt» → «Basel-Stadt»
    sauberer_name = (
        kanton_name.replace("Kanton ", "")
        .replace("Canton de ", "")
        .replace("Canton du ", "")
        .replace("Cantone ", "")
        .strip()
    )
    kuerzel = KANTONE.get(sauberer_name)
    heute = date.today()

    url = "https://openholidaysapi.org/PublicHolidays"
    params = {
        "countryIsoCode": "CH",
        "languageIsoCode": "DE",
        "validFrom": heute.isoformat(),
        "validTo": (heute + timedelta(days=365)).isoformat(),
    }
    antwort = requests.get(url, params=params, headers={"accept": "application/json"})
    feiertage = antwort.json()

    # nach Datum sortieren, den ersten passenden nehmen
    feiertage.sort(key=lambda f: f["startDate"])
    for feiertag in feiertage:
        if gilt_im_kanton(feiertag, kuerzel):
            datum = date.fromisoformat(feiertag["startDate"])
            return {
                "canton": kuerzel or sauberer_name,
                "date": feiertag["startDate"],
                "name": deutscher_name(feiertag),
                "days_until": (datum - heute).days,
            }
    return None