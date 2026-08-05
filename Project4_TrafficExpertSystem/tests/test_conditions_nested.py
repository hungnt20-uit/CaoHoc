from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.engine.conditions import eval_cond_node


def test_any_group():
    wm = WorkingMemory({"chiso.nongDoCon_mau": 90})
    node = {"any": ["chiso.nongDoCon_khiTho > 0.4", "chiso.nongDoCon_mau > 80"]}
    assert eval_cond_node(node, wm) is True


def test_all_group_nested_in_any():
    wm = WorkingMemory({"chiso.nongDoCon_mau": 60})
    node = {
        "any": [
            {"all": ["chiso.nongDoCon_khiTho > 0.25", "chiso.nongDoCon_khiTho <= 0.4"]},
            {"all": ["chiso.nongDoCon_mau > 50", "chiso.nongDoCon_mau <= 80"]},
        ]
    }
    assert eval_cond_node(node, wm) is True


def test_plain_string_still_works():
    wm = WorkingMemory({"chiso.tocDo": 90})
    assert eval_cond_node("chiso.tocDo > 50", wm) is True
