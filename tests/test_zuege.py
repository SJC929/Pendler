import pytest
import requests

import zuege
from zuege import dauer_schoen, verkehrsmittel, erstes_fahrzeug, FahrplanNichtErreichbar


# ---------- dauer_schoen ----------

def test_dauer_mit_stunden():
    assert dauer_schoen("00d01:05:00") == "1h 05min"


def test_dauer_nur_minuten():
    assert dauer_schoen("00d00:12:00") == "12 min"


def test_dauer_ueber_einen_tag():
    assert dauer_schoen("01d02:30:00") == "26h 30min"


# ---------- verkehrsmittel ----------

def test_bus_wird_erkannt():
    assert verkehrsmittel("B") == "bus"


def test_tram_wird_erkannt():
    assert verkehrsmittel("T") == "tram"


def test_zug_ist_standard():
    assert verkehrsmittel("IR") == "train"


def test_leere_kategorie_ist_zug():
    assert verkehrsmittel(None) == "train"


# ---------- erstes_fahrzeug ----------

def test_fussweg_wird_uebersprungen():
    verbindung = {
        "sections": [
            {"journey": None, "walk": {"duration": 120}},
            {"journey": {"category": "B", "number": "48"}},
        ]
    }
    assert erstes_fahrzeug(verbindung) == ("B", "48")


# ---------- Fehlerbehandlung ----------

def test_zeitueberschreitung_gibt_eigenen_fehler(monkeypatch):
    def tut_so_als_ob_timeout(*args, **kwargs):
        raise requests.Timeout("zu langsam")

    # requests.get wird für diesen Test durch eine Attrappe ersetzt
    monkeypatch.setattr(zuege.requests, "get", tut_so_als_ob_timeout)

    with pytest.raises(FahrplanNichtErreichbar):
        zuege.search_stations("Basel")