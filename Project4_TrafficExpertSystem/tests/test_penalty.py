from traffic_es.engine.penalty import aggregate
from traffic_es.knowledge.rules import Rule, KetLuan, CanCu, PhatBoSung


def _rule(rid, tmin, tmax, tuoc=None):
    return Rule(
        id=rid,
        nhom="x",
        dieu_kien=[],
        ket_luan=KetLuan(
            hanh_vi=rid,
            tien_phat_min=tmin,
            tien_phat_max=tmax,
            phat_bo_sung=PhatBoSung(tuoc_gplx_thang=tuoc),
            can_cu=CanCu(nghi_dinh="168", dieu=6),
        ),
    )


def test_sum_avg_when_no_aggravation():
    res = aggregate([_rule("A", 10, 20), _rule("B", 30, 50)], pick=None)
    # trung bình khung: 15 + 40 = 55
    assert res.tong_tien == 55
    assert len(res.chi_tiet) == 2


def test_sum_max_when_aggravated():
    res = aggregate([_rule("A", 10, 20), _rule("B", 30, 50)], pick="max")
    assert res.tong_tien == 70  # 20 + 50


def test_supplementary_takes_longest_suspension():
    res = aggregate(
        [_rule("A", 10, 20, tuoc=[10, 12]), _rule("B", 30, 50, tuoc=[22, 24])],
        pick="max",
    )
    assert res.tuoc_gplx_thang_max == 24
