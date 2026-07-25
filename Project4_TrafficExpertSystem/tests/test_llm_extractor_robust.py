from traffic_es.llm.client import FakeLLM
from traffic_es.nlu.llm_extractor import LLMExtractor


def test_strips_code_fence_and_grounds():
    raw = (
        "```json\n"
        '{"facts": {"phuongtien.loai": "o_to", "chiso.nongDoCon_khiTho": "0.42", "foo.bar": 1}, '
        '"raw_events": ["đâm xe"]}\n'
        "```"
    )
    llm = FakeLLM(responses={"cồn": raw})
    facts, ev, events = LLMExtractor(llm).extract("lái ô tô cồn 0.42")
    assert facts["phuongtien.loai"] == "o_to"
    assert facts["chiso.nongDoCon_khiTho"] == 0.42  # ép chuỗi -> số
    assert "foo.bar" not in facts  # grounding loại node lạ
    assert "đâm xe" in events


def test_invalid_json_returns_empty():
    llm = FakeLLM(responses={"x": "không phải JSON gì cả"})
    facts, ev, events = LLMExtractor(llm).extract("x")
    assert facts == {} and events == []
