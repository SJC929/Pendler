from station import gruppieren


def test_gruppieren_und_sortieren():
    zeilen = [
        ("BVB", "36", "Kleinhüningen", 10, 22),
        ("BVB", "6", "Allschwil Dorf", 10, 7),
        ("BVB", "6", "Allschwil Dorf", 11, 8),
        ("BLT", "11", "Aesch Dorf", 10, 9),
    ]
    linien = gruppieren(zeilen)
    assert [l["linie"] for l in linien] == ["6", "11", "36"]
    assert linien[0]["stunden"] == [{"stunde": 10, "risiko": 7}, {"stunde": 11, "risiko": 8}]