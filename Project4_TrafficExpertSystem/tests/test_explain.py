from pathlib import Path

from traffic_es.engine.reasoner import Reasoner
from traffic_es.explain.generator import render_explanation


def test_explanation_mentions_cancu_and_total():
    r = Reasoner.from_rules_dir(Path("traffic_es/knowledge/rules"))
    res = r.infer(
        {
            "phuongtien.loai": "o_to",
            "chiso.nongDoCon_khiTho": 0.42,
            "tinhtiet.gay_tai_nan": True,
        }
    )
    text = render_explanation(res.trace, res.ket_qua)
    assert "Điều 6" in text
    assert "40.000.000" in text
    assert "tước" in text.lower()
