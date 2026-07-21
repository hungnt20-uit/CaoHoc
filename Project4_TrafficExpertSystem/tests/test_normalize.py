from traffic_es.nlu.normalize import normalize


def test_decimal_comma_to_dot():
    assert "0.42" in normalize("nồng độ cồn 0,42 mg/l")


def test_expand_abbreviations():
    out = normalize("nđc 0.3 trong kdc")
    assert "nồng độ cồn" in out and "khu dân cư" in out


def test_lowercase_preserved_content():
    assert "ô tô" in normalize("Tôi lái Ô Tô").lower()
