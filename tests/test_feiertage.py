from feiertage import gilt_im_kanton, deutscher_name


def test_nationaler_feiertag_gilt_ueberall():
    feiertag = {"nationwide": True, "subdivisions": []}
    assert gilt_im_kanton(feiertag, "ZH") is True


def test_kantonaler_feiertag_gilt_im_kanton():
    feiertag = {"nationwide": False, "subdivisions": [{"code": "CH-LU"}]}
    assert gilt_im_kanton(feiertag, "LU") is True


def test_kantonaler_feiertag_gilt_nicht_in_anderem_kanton():
    feiertag = {"nationwide": False, "subdivisions": [{"code": "CH-LU"}]}
    assert gilt_im_kanton(feiertag, "ZH") is False


def test_deutscher_name_wird_gefunden():
    feiertag = {"name": [
        {"language": "FR", "text": "Noël"},
        {"language": "DE", "text": "Weihnachten"},
    ]}
    assert deutscher_name(feiertag) == "Weihnachten"