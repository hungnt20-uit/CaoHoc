from pathlib import Path

from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.engine.trace import Trace
from traffic_es.engine.funcs import DEFAULT_FUNCS
from traffic_es.engine.deduction_network import goal_attrs, solve_and_apply
from traffic_es.knowledge.kb_loader import load_rules

RULES_DIR = Path("traffic_es/knowledge/rules")


def test_goal_attrs_speed():
    rules = load_rules(RULES_DIR)
    wm = WorkingMemory({"chiso.tocDo": 75.0, "chiso.tocDoGioiHan": 50.0})
    goals = goal_attrs(rules, DEFAULT_FUNCS, wm)
    assert "chiso.vuot_toc_do_kmh" in goals


def test_solve_applies_and_traces_astar():
    rules = load_rules(RULES_DIR)
    wm = WorkingMemory({"chiso.tocDo": 75.0, "chiso.tocDoGioiHan": 50.0})
    tr = Trace()
    solve_and_apply(wm, DEFAULT_FUNCS, rules, tr)
    assert wm.get("chiso.vuot_toc_do_kmh") == 25.0
    assert any(s.kind == "ASTAR" for s in tr.steps)


def test_no_goal_no_astar_for_con():
    # nồng độ cồn không cần thuộc tính dẫn xuất -> không có bước ASTAR
    rules = load_rules(RULES_DIR)
    wm = WorkingMemory({"chiso.nongDoCon_khiTho": 0.42})
    tr = Trace()
    solve_and_apply(wm, DEFAULT_FUNCS, rules, tr)
    assert not any(s.kind == "ASTAR" for s in tr.steps)
