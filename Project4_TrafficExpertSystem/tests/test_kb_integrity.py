from pathlib import Path

from traffic_es.knowledge.kb_loader import load_rules

RULES_DIR = Path("traffic_es/knowledge/rules")


def test_rule_ids_unique():
    rules = load_rules(RULES_DIR)
    ids = [r.id for r in rules]
    assert len(ids) == len(set(ids)), "Có id luật trùng nhau"


def test_every_rule_has_valid_penalty_and_cancu():
    for r in load_rules(RULES_DIR):
        assert r.ket_luan.tien_phat_min <= r.ket_luan.tien_phat_max, r.id
        assert r.ket_luan.can_cu.nghi_dinh, r.id
        assert r.ket_luan.can_cu.dieu > 0, r.id


def _leaf_conditions(node):
    """Trả về danh sách chuỗi điều kiện lá từ node str | {'any'|'all': [...]}."""
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        out = []
        for key in ("any", "all"):
            for child in node.get(key, []):
                out.extend(_leaf_conditions(child))
        return out
    return []


def test_conditions_reference_known_namespaces():
    ok = ("phuongtien.", "nguoi.", "chiso.", "boicanh.", "tinhtiet.", "hanhvi.")
    for r in load_rules(RULES_DIR):
        for node in r.dieu_kien:
            for cond in _leaf_conditions(node):
                assert cond.startswith(ok), f"{r.id}: điều kiện lạ {cond!r}"
