from verkehr import auswerten, abstand_km


def fake_antwort():
    punkte = [{"latitude": 47.55, "longitude": 7.55 + i * 0.1} for i in range(10)]
    return {"routes": [{
        "summary": {
            "lengthInMeters": 87300,
            "travelTimeInSeconds": 4320,            # 72 Min.
            "noTrafficTravelTimeInSeconds": 3240,   # 54 Min.
            "trafficDelayInSeconds": 1080,          # 18 Min.
            "arrivalTime": "2026-11-03T16:22:00+01:00",
        },
        "legs": [{"points": punkte}],
        "sections": [
            {"sectionType": "TRAFFIC", "simpleCategory": "JAM", "delayInSeconds": 840,
             "effectiveSpeedInKmh": 23, "startPointIndex": 4},
            {"sectionType": "TRAFFIC", "simpleCategory": "OTHER", "delayInSeconds": 30,
             "startPointIndex": 7},                 # unter 1 Min. → ignorieren
        ],
    }]}


def test_auswerten_zeiten():
    ergebnis = auswerten(fake_antwort())
    assert ergebnis["dauer_min"] == 72
    assert ergebnis["ohne_stau_min"] == 54
    assert ergebnis["stau_min"] == 18
    assert ergebnis["ankunft"] == "16:22"


def test_auswerten_staus():
    staus = auswerten(fake_antwort())["staus"]
    assert len(staus) == 1
    assert staus[0]["art"] == "Stau"
    assert staus[0]["verzoegerung_min"] == 14
    assert staus[0]["bei_km"] > 0


def test_abstand_basel_zuerich():
    basel = {"latitude": 47.56, "longitude": 7.59}
    zuerich = {"latitude": 47.37, "longitude": 8.54}
    assert 70 < abstand_km(basel, zuerich) < 80   # Luftlinie ca. 75 km

from verkehr import treffer_auswerten


def test_treffer_adresse():
    treffer = {"address": {"freeformAddress": "Dürrenmattweg 8, 4123 Allschwil"},
               "position": {"lat": 47.55, "lon": 7.54}}
    assert treffer_auswerten(treffer) == {"name": "Dürrenmattweg 8, 4123 Allschwil", "lat": 47.55, "lon": 7.54}


def test_treffer_mit_ortsname():
    treffer = {"poi": {"name": "Messe Basel"}, "address": {"freeformAddress": "Messeplatz, 4058 Basel"},
               "position": {"lat": 47.56, "lon": 7.60}}
    assert treffer_auswerten(treffer)["name"] == "Messe Basel, Messeplatz, 4058 Basel"