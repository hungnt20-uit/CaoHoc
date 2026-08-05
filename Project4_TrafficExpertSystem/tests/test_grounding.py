from traffic_es.nlu.grounding import ground


def test_keeps_known_and_drops_unknown():
    facts = {"phuongtien.loai": "o_to", "chiso.nongDoCon_khiTho": 0.4, "foo.bar": 1}
    clean, warns = ground(facts)
    assert "phuongtien.loai" in clean and "foo.bar" not in clean
    assert any("foo.bar" in w for w in warns)


def test_flags_out_of_range():
    clean, warns = ground({"chiso.nongDoCon_khiTho": 99})
    assert "chiso.nongDoCon_khiTho" not in clean
    assert any("miền" in w for w in warns)
