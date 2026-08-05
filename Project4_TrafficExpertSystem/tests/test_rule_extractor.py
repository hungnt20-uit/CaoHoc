import json

from traffic_es.llm.client import FakeLLM
from traffic_es.acquisition.segmenter import Clause
from traffic_es.acquisition.rule_extractor import extract_rules
from traffic_es.knowledge.rules import Rule


def _clause():
    return Clause(
        dieu=6,
        dieu_title="Xử phạt người điều khiển xe ô tô",
        khoan=11,
        diem="a",
        text="Điều khiển xe trên đường mà trong hơi thở có nồng độ cồn vượt quá 0,4 miligam/1 lít khí thở.",
    )


def test_extract_builds_valid_rule():
    llm = FakeLLM(
        responses={
            "nồng độ cồn": json.dumps(
                {
                    "nhom": "nong_do_con",
                    "ap_dung_loai_xe": ["o_to"],
                    "dieu_kien": ["chiso.nongDoCon_khiTho > 0.4"],
                    "hanh_vi": "Điều khiển ô tô mà trong hơi thở có nồng độ cồn vượt quá 0,4 mg/l",
                }
            )
        }
    )
    rules = extract_rules(
        _clause(), nghi_dinh="168/2024/NĐ-CP", llm=llm, tien_min=30000000, tien_max=40000000
    )
    assert len(rules) == 1
    r = rules[0]
    assert isinstance(r, Rule)
    assert r.ket_luan.tien_phat_max == 40000000  # từ clause, KHÔNG từ LLM
    assert r.ket_luan.can_cu.dieu == 6 and r.ket_luan.can_cu.khoan == 11
    assert r.ket_luan.can_cu.diem == "a"
    assert r.nhom == "nong_do_con"


def test_extract_returns_empty_on_blank_llm():
    llm = FakeLLM(responses={})  # trả "" -> không phải hành vi phạt
    rules = extract_rules(
        _clause(), nghi_dinh="168/2024/NĐ-CP", llm=llm, tien_min=0, tien_max=0
    )
    assert rules == []
