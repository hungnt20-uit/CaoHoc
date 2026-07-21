from pathlib import Path

from traffic_es.knowledge.kb_loader import load_rules
from traffic_es.knowledge.rules import Rule

RULES_DIR = Path("traffic_es/knowledge/rules")


def test_load_rules_returns_rule_objects():
    rules = load_rules(RULES_DIR)
    assert len(rules) >= 1
    assert all(isinstance(r, Rule) for r in rules)


def test_rule_has_cancu_and_conditions():
    rules = load_rules(RULES_DIR)
    r = next(r for r in rules if r.id == "R_CON_OTO_MUC3")
    assert r.ket_luan.can_cu.nghi_dinh == "168/2024/NĐ-CP"
    assert r.ket_luan.can_cu.dieu == 6
    # điều kiện có thể lồng trong node any/all — kiểm tra phẳng
    assert "chiso.nongDoCon_khiTho > 0.4" in str(r.dieu_kien)
    assert r.ket_luan.tien_phat_max == 40000000
