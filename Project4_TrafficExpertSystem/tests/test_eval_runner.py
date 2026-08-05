from pathlib import Path

from eval.dataset import Case
from eval.runner import evaluate

RULES_DIR = Path("traffic_es/knowledge/rules")


def test_evaluate_aggregates():
    cases = [
        Case(
            "c01",
            "Tôi lái ô tô, thổi nồng độ cồn 0.42 mg/l",
            {
                "facts": {"phuongtien.loai": "o_to", "chiso.nongDoCon_khiTho": 0.42},
                "rule_ids": ["R_CON_OTO_MUC3"],
                "tong_tien": 35000000,
            },
        )
    ]
    rep = evaluate(cases, RULES_DIR)
    assert rep["n"] == 1
    assert rep["conclusion_acc"] == 1.0
    assert rep["money_acc"] == 1.0
    assert rep["per_case"][0]["fired"] == ["R_CON_OTO_MUC3"]
