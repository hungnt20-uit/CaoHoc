from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.engine.trace import Trace
from traffic_es.engine.forward_chaining import deduce_rules, apply_meta
from traffic_es.knowledge.rules import Rule, KetLuan, CanCu, MetaRule


def _rule():
    return Rule(
        id="R1",
        nhom="nong_do_con",
        ap_dung_loai_xe=["o_to"],
        dieu_kien=["chiso.nongDoCon_khiTho > 0.4"],
        ket_luan=KetLuan(
            hanh_vi="Nồng độ cồn > 0,4",
            tien_phat_min=30000000,
            tien_phat_max=40000000,
            can_cu=CanCu(nghi_dinh="168/2024/NĐ-CP", dieu=6),
        ),
    )


def test_rule_fires_when_condition_met():
    wm = WorkingMemory({"phuongtien.loai": "o_to", "chiso.nongDoCon_khiTho": 0.42})
    tr = Trace()
    fired = deduce_rules(wm, [_rule()], tr)
    assert [r.id for r in fired] == ["R1"]
    assert any(s.kind == "RULE" for s in tr.steps)


def test_rule_skipped_when_vehicle_mismatch():
    wm = WorkingMemory({"phuongtien.loai": "xe_may", "chiso.nongDoCon_khiTho": 0.42})
    fired = deduce_rules(wm, [_rule()], Trace())
    assert fired == []


def test_meta_selects_max():
    wm = WorkingMemory({"tinhtiet.gay_tai_nan": True})
    meta = MetaRule(
        id="M1",
        loai="tinh_tiet",
        dieu_kien=["tinhtiet.gay_tai_nan == true"],
        chon_muc="max",
    )
    picks = apply_meta(wm, [meta], Trace())
    assert picks == "max"
