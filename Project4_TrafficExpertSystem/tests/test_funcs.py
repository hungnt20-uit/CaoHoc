from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.engine.trace import Trace
from traffic_es.engine.funcs import Func, apply_funcs, DEFAULT_FUNCS


def test_vuot_toc_do_pct():
    wm = WorkingMemory({"chiso.tocDo": 90, "chiso.tocDoGioiHan": 50})
    tr = Trace()
    apply_funcs(wm, DEFAULT_FUNCS, tr)
    assert wm.get("chiso.vuot_toc_do_pct") == 80.0
    assert any(s.kind == "FUNC" for s in tr.steps)


def test_func_not_fired_when_inputs_missing():
    wm = WorkingMemory({"chiso.tocDo": 90})  # thiếu tocDoGioiHan
    tr = Trace()
    apply_funcs(wm, DEFAULT_FUNCS, tr)
    assert not wm.has("chiso.vuot_toc_do_pct")


def test_chained_funcs_reach_fixpoint():
    f1 = Func("f_double", ["a"], "b", lambda wm: wm.get("a") * 2)
    f2 = Func("f_inc", ["b"], "c", lambda wm: wm.get("b") + 1)
    wm = WorkingMemory({"a": 3})
    tr = Trace()
    apply_funcs(wm, [f1, f2], tr)
    assert wm.get("b") == 6 and wm.get("c") == 7
