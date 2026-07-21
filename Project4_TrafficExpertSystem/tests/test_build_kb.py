import json

from traffic_es.llm.client import FakeLLM
from traffic_es.acquisition.build_kb import build_kb_from_text, write_rules_yaml
from traffic_es.knowledge.kb_loader import load_rules

TEXT = (
    "Điều 6. Xử phạt người điều khiển xe ô tô\n"
    "11. Phạt tiền từ 30.000.000 đồng đến 40.000.000 đồng đối với người điều khiển xe:\n"
    "a) Điều khiển xe trên đường mà trong hơi thở có nồng độ cồn vượt quá 0,4 miligam/1 lít khí thở.\n"
)


def _llm():
    return FakeLLM(
        responses={
            "nồng độ cồn": json.dumps(
                {
                    "nhom": "nong_do_con",
                    "ap_dung_loai_xe": ["o_to"],
                    "dieu_kien": ["chiso.nongDoCon_khiTho > 0.4"],
                    "hanh_vi": "Điều khiển ô tô nồng độ cồn > 0,4 mg/l",
                }
            )
        }
    )


def test_build_extracts_rule_with_money_from_text():
    rules = build_kb_from_text(TEXT, nghi_dinh="168/2024/NĐ-CP", llm=_llm())
    assert len(rules) == 1
    assert rules[0].ket_luan.tien_phat_min == 30000000
    assert rules[0].ket_luan.tien_phat_max == 40000000


def test_write_and_reload_roundtrip(tmp_path):
    rules = build_kb_from_text(TEXT, nghi_dinh="168/2024/NĐ-CP", llm=_llm())
    out = tmp_path / "generated.yaml"
    write_rules_yaml(rules, out)
    reloaded = load_rules(tmp_path)
    assert [r.id for r in reloaded] == [r.id for r in rules]
