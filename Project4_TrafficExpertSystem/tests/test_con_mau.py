from pathlib import Path

from traffic_es.engine.reasoner import Reasoner

RULES_DIR = Path("traffic_es/knowledge/rules")


def test_con_mau_only():
    r = Reasoner.from_rules_dir(RULES_DIR)
    # chỉ có nồng độ cồn trong MÁU (không có khí thở)
    res = r.infer({"phuongtien.loai": "o_to", "chiso.nongDoCon_mau": 90})
    assert res.ket_qua.tong_tien == 35000000  # (30+40)/2 khung mức 3
    assert any(
        s.data.get("rule_id") == "R_CON_OTO_MUC3"
        for s in res.trace.steps
        if s.kind == "RULE"
    )


def test_con_mau_muc2():
    r = Reasoner.from_rules_dir(RULES_DIR)
    res = r.infer({"phuongtien.loai": "o_to", "chiso.nongDoCon_mau": 60})
    assert res.ket_qua.chi_tiet[0].can_cu.startswith("Điều 6, Khoản 9")


def test_con_khiTho_still_works():
    r = Reasoner.from_rules_dir(RULES_DIR)
    res = r.infer({"phuongtien.loai": "o_to", "chiso.nongDoCon_khiTho": 0.42})
    assert res.ket_qua.chi_tiet[0].can_cu.startswith("Điều 6, Khoản 11")
