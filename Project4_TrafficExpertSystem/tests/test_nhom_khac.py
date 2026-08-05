from pathlib import Path

from traffic_es.engine.reasoner import Reasoner

RULES_DIR = Path("traffic_es/knowledge/rules")


def _R():
    return Reasoner.from_rules_dir(RULES_DIR)


def test_mu_bao_hiem():
    res = _R().infer({"phuongtien.loai": "xe_may", "nguoi.khong_mu_bao_hiem": True})
    assert res.ket_qua.chi_tiet[0].can_cu.startswith("Điều 7")
    assert res.ket_qua.tong_tien == 500000  # (400+600)/2


def test_vuot_den_do_oto():
    res = _R().infer({"phuongtien.loai": "o_to", "hanhvi.vuot_den_do": True})
    assert res.ket_qua.tong_tien == 19000000  # (18+20)/2


def test_khong_gplx_xemay():
    res = _R().infer({"phuongtien.loai": "xe_may", "nguoi.coGPLX": False})
    assert res.ket_qua.tong_tien == 3000000  # (2+4)/2


def test_day_an_toan_oto():
    res = _R().infer({"phuongtien.loai": "o_to", "nguoi.khong_day_an_toan": True})
    assert res.ket_qua.chi_tiet[0].can_cu.startswith("Điều 6")
