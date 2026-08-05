from traffic_es.engine.conditions import referenced_keys


def test_leaf_lhs_key():
    assert referenced_keys("chiso.vuot_toc_do_kmh >= 5") == {"chiso.vuot_toc_do_kmh"}


def test_key_vs_key():
    assert referenced_keys("chiso.tocDo > chiso.tocDoGioiHan") == {
        "chiso.tocDo",
        "chiso.tocDoGioiHan",
    }


def test_ignores_literals():
    assert referenced_keys('boicanh.khuVuc == "khu_dan_cu"') == {"boicanh.khuVuc"}


def test_nested_any_all():
    node = {
        "any": [
            {"all": ["chiso.nongDoCon_khiTho > 0.25", "chiso.nongDoCon_khiTho <= 0.4"]},
            {"all": ["chiso.nongDoCon_mau > 50", "chiso.nongDoCon_mau <= 80"]},
        ]
    }
    assert referenced_keys(node) == {"chiso.nongDoCon_khiTho", "chiso.nongDoCon_mau"}
