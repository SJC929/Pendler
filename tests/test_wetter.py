from wetter import will_it_rain, pollen_level


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