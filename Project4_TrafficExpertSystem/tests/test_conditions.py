import pytest

from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.engine.conditions import eval_condition


def test_numeric_gt_true():
    wm = WorkingMemory({"chiso.nongDoCon_khiTho": 0.42})
    assert eval_condition("chiso.nongDoCon_khiTho > 0.4", wm) is True


def test_numeric_gt_false():
    wm = WorkingMemory({"chiso.nongDoCon_khiTho": 0.2})
    assert eval_condition("chiso.nongDoCon_khiTho > 0.4", wm) is False


def test_bool_eq():
    wm = WorkingMemory({"tinhtiet.gay_tai_nan": True})
    assert eval_condition("tinhtiet.gay_tai_nan == true", wm) is True


def test_string_eq():
    wm = WorkingMemory({"boicanh.khuVuc": "khu_dan_cu"})
    assert eval_condition('boicanh.khuVuc == "khu_dan_cu"', wm) is True


def test_key_vs_key():
    wm = WorkingMemory({"chiso.tocDo": 90, "chiso.tocDoGioiHan": 50})
    assert eval_condition("chiso.tocDo > chiso.tocDoGioiHan", wm) is True


def test_missing_key_is_false():
    wm = WorkingMemory({})
    assert eval_condition("chiso.tocDo > 50", wm) is False


def test_bad_syntax_raises():
    wm = WorkingMemory({})
    with pytest.raises(ValueError):
        eval_condition("chiso.tocDo 50", wm)
