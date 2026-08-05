from pathlib import Path

from traffic_es.engine.reasoner import Reasoner

RULES_DIR = Path("traffic_es/knowledge/rules")


def _infer(loai, tocDo, gh=50):
    r = Reasoner.from_rules_dir(RULES_DIR)
    return r.infer(
        {"phuongtien.loai": loai, "chiso.tocDo": tocDo, "chiso.tocDoGioiHan": gh}
    )


def test_oto_vuot_25kmh():
    res = _infer("o_to", 75)  # vượt 25 km/h -> mức >20-35
    assert res.ket_qua.tong_tien == 7000000  # (6+8)/2
    assert res.ket_qua.chi_tiet[0].can_cu.startswith("Điều 6, Khoản 6")


def test_oto_vuot_40kmh():
    res = _infer("o_to", 90)  # vượt 40 km/h -> mức >35
    assert res.ket_qua.tong_tien == 13000000  # (12+14)/2


def test_xemay_vuot_15kmh():
    res = _infer("xe_may", 65)  # vượt 15 -> mức 10-20
    assert res.ket_qua.chi_tiet[0].can_cu.startswith("Điều 7")


def test_khong_vuot():
    res = _infer("o_to", 52)  # vượt 2 km/h -> không thuộc mức phạt
    assert res.ket_qua.tong_tien == 0
