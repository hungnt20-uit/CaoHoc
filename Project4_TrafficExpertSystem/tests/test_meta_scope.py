from pathlib import Path

from traffic_es.engine.forward_chaining import apply_meta
from traffic_es.engine.reasoner import Reasoner
from traffic_es.engine.trace import Trace
from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.knowledge.rules import CanCu, KetLuan, MetaRule, Rule

RULES_DIR = Path("traffic_es/knowledge/rules")


def _rule(rid: str, nhom: str) -> Rule:
    return Rule(
        id=rid,
        nhom=nhom,
        dieu_kien=[],
        ket_luan=KetLuan(
            hanh_vi=rid,
            tien_phat_min=100,
            tien_phat_max=200,
            can_cu=CanCu(nghi_dinh="168/2024/NĐ-CP", dieu=6),
        ),
    )


def _meta(mid: str, fact: str, muc: str, nhom=None) -> MetaRule:
    return MetaRule(
        id=mid,
        loai="tinh_tiet",
        dieu_kien=[f"{fact} == true"],
        chon_muc=muc,
        ap_dung_nhom=nhom or [],
    )


def test_meta_only_applies_to_declared_groups():
    wm = WorkingMemory({"tinhtiet.gay_tai_nan": True})
    fired = [_rule("R_CON", "nong_do_con"), _rule("R_DAY", "day_an_toan")]
    meta = [_meta("M", "tinhtiet.gay_tai_nan", "max", ["nong_do_con"])]
    picks = apply_meta(wm, meta, Trace(), fired)
    assert picks == {"R_CON": "max", "R_DAY": None}


def test_conflicting_meta_offsets_to_average_regardless_of_order():
    wm = WorkingMemory({"tinhtiet.tai_pham": True, "tinhtiet.tu_nguyen_khai_bao": True})
    fired = [_rule("R", "nong_do_con")]
    up = _meta("M_UP", "tinhtiet.tai_pham", "max")
    down = _meta("M_DOWN", "tinhtiet.tu_nguyen_khai_bao", "min")
    assert apply_meta(wm, [up, down], Trace(), fired) == {"R": None}
    assert apply_meta(wm, [down, up], Trace(), fired) == {"R": None}


def test_meta_supports_nested_condition_like_rules():
    wm = WorkingMemory({"tinhtiet.tai_pham": True})
    meta = MetaRule(
        id="M_NEST",
        loai="tinh_tiet",
        dieu_kien=[{"any": ["tinhtiet.gay_tai_nan == true", "tinhtiet.tai_pham == true"]}],
        chon_muc="max",
    )
    assert apply_meta(wm, [meta], Trace(), [_rule("R", "toc_do")]) == {"R": "max"}


def test_accident_does_not_aggravate_unrelated_static_offence():
    reasoner = Reasoner.from_rules_dir(RULES_DIR)
    base = {
        "phuongtien.loai": "o_to",
        "chiso.nongDoCon_khiTho": 0.45,
        "nguoi.khong_day_an_toan": True,
    }
    without = reasoner.infer(base)
    with_accident = reasoner.infer({**base, "tinhtiet.gay_tai_nan": True})

    def _tien(res, prefix):
        return next(d.tien for d in res.ket_qua.chi_tiet if d.hanh_vi.startswith(prefix))

    # Lỗi cồn bị đẩy lên mức tối đa, lỗi dây an toàn giữ nguyên mức trung bình.
    assert _tien(with_accident, "Điều khiển ô tô") > _tien(without, "Điều khiển ô tô")
    assert _tien(with_accident, "Không thắt dây") == _tien(without, "Không thắt dây")
