from pathlib import Path

from traffic_es.engine.reasoner import Reasoner

RULES_DIR = Path("traffic_es/knowledge/rules")


def test_end_to_end_con_oto():
    reasoner = Reasoner.from_rules_dir(RULES_DIR)
    facts = {
        "phuongtien.loai": "o_to",
        "chiso.nongDoCon_khiTho": 0.42,
        "tinhtiet.gay_tai_nan": True,
    }
    res = reasoner.infer(facts)
    assert res.ket_qua.tong_tien == 40000000  # có tăng nặng -> mức max
    assert res.ket_qua.tuoc_gplx_thang_max == 24
    assert any(
        s.data.get("rule_id") == "R_CON_OTO_MUC3"
        for s in res.trace.steps
        if s.kind == "RULE"
    )
    assert any(s.kind == "META" for s in res.trace.steps)


def test_speed_uses_astar_network():
    reasoner = Reasoner.from_rules_dir(RULES_DIR)
    facts = {
        "phuongtien.loai": "o_to",
        "chiso.tocDo": 80.0,
        "chiso.tocDoGioiHan": 50.0,
    }
    res = reasoner.infer(facts)
    astar = [s for s in res.trace.steps if s.kind == "ASTAR"]
    assert astar, "phải có bước suy diễn bằng mạng tính toán (A*)"
    assert "vuot_toc_do_kmh" in astar[0].data["solution"]
    assert res.ket_qua.tong_tien > 0


def test_no_violation_returns_empty():
    reasoner = Reasoner.from_rules_dir(RULES_DIR)
    res = reasoner.infer({"phuongtien.loai": "o_to", "chiso.nongDoCon_khiTho": 0.0})
    assert res.ket_qua.chi_tiet == []
    assert res.ket_qua.tong_tien == 0
