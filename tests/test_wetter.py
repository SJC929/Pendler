from wetter import will_it_rain, pollen_level

from datetime import datetime

from wetter import regen_stufe, pendel_regen


# ---------- will_it_rain ----------

def test_regen_ab_50_prozent():
    assert will_it_rain([0, 10, 50, 20]) is True


def test_kein_regen_unter_50_prozent():
    assert will_it_rain([0, 10, 49, 20]) is False


# ---------- pollen_level ----------

def test_keine_pollen():
    assert pollen_level(0) == ("none", "keine")


def test_schwache_pollen():
    assert pollen_level(10) == ("low", "schwach")


def test_maessige_pollen():
    assert pollen_level(50) == ("moderate", "mässig")


def test_starke_pollen():
    assert pollen_level(150) == ("high", "stark")




def test_regen_stufe():
    assert regen_stufe(70, 1.5) == "regen"
    assert regen_stufe(80, 0.1) == "vielleicht"   # hohe Wahrscheinlichkeit, aber nur Niesel
    assert regen_stufe(35, 0.0) == "vielleicht"
    assert regen_stufe(10, 0.0) == "trocken"


def fake_daten():
    zeiten = [f"2026-11-0{t}T{h:02d}:00" for t in (3, 4) for h in range(24)]
    wahrscheinlichkeit = [0] * 48
    menge = [0.0] * 48
    wahrscheinlichkeit[17], menge[17] = 70, 1.2          # heute 17 Uhr: Regen
    wahrscheinlichkeit[24 + 7] = 35                      # morgen 07 Uhr: vielleicht
    return {"hourly": {"time": zeiten, "precipitation_probability": wahrscheinlichkeit, "precipitation": menge}}


def test_pendel_regen_heute():
    jetzt = datetime(2026, 11, 3, 12, 0)
    ergebnis = pendel_regen(fake_daten(), "17:00", jetzt)
    assert ergebnis["tag"] == "heute"
    assert ergebnis["stufe"] == "regen"


def test_pendel_regen_springt_auf_morgen():
    jetzt = datetime(2026, 11, 3, 12, 0)                 # 07:30 ist heute schon vorbei
    ergebnis = pendel_regen(fake_daten(), "07:30", jetzt)
    assert ergebnis["tag"] == "morgen"
    assert ergebnis["stufe"] == "vielleicht"