from traffic_es.engine.penalty import aggregate
from traffic_es.knowledge.rules import Rule, KetLuan, CanCu, PhatBoSung


def _r(rid, diem):
    return Rule(
        id=rid,
        nhom="x",
        dieu_kien=[],
        ket_luan=KetLuan(
            hanh_vi=rid,
            tien_phat_min=1,
            tien_phat_max=2,
            phat_bo_sung=PhatBoSung(tru_diem=diem),
            can_cu=CanCu(nghi_dinh="168", dieu=6),
        ),
    )


def test_tru_diem_max():
    res = aggregate([_r("A", 4), _r("B", 10)], pick=None)
    assert res.tru_diem_max == 10
