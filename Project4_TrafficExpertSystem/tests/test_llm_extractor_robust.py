from traffic_es.llm.client import FakeLLM
from traffic_es.nlu.llm_extractor import LLMExtractor


def test_strips_code_fence_and_grounds():
    raw = (
        "```json\n"
        '{"facts": {"phuongtien.loai": {"value": "o_to", "nguon": "ô tô"},'
        ' "chiso.nongDoCon_khiTho": {"value": "0.42", "nguon": "cồn 0.42"},'
        ' "foo.bar": {"value": "x", "nguon": "lái"}},'
        ' "raw_events": ["đâm xe"]}\n'
        "```"
    )
    llm = FakeLLM(responses={"cồn": raw})
    facts, ev, events = LLMExtractor(llm).extract("lái ô tô cồn 0.42")
    assert facts["phuongtien.loai"] == "o_to"
    assert facts["chiso.nongDoCon_khiTho"] == 0.42  # ép chuỗi -> số
    assert "foo.bar" not in facts  # grounding loại node lạ
    assert "đâm xe" in events


def test_accepts_fact_list_shape_from_small_local_models():
    """Model nhỏ chạy local hay trả `facts` dạng mảng thay vì map — không được sập."""
    raw = (
        '{"facts": [{"key": "phuongtien.loai", "value": "o_to", "nguon": "ô tô"},'
        ' {"key": "chiso.nongDoCon_khiTho", "value": "0.45", "nguon": "0.45"},'
        ' {"key": "foo.bar", "value": "x", "nguon": "ô tô"}, "rác", {"thieu": "key"}],'
        ' "raw_events": "tôi có va chạm"}'
    )
    llm = FakeLLM(responses={"ô tô": raw})
    facts, _ev, events = LLMExtractor(llm).extract("lái ô tô, cồn 0.45")
    assert facts == {"phuongtien.loai": "o_to", "chiso.nongDoCon_khiTho": 0.45}
    assert events == ["tôi có va chạm"]


def test_wrong_types_for_facts_and_events_degrade_to_empty():
    raw = '{"facts": "o_to", "raw_events": {"a": 1}}'
    facts, _ev, events = LLMExtractor(FakeLLM(responses={"x": raw})).extract("x")
    assert facts == {} and events == []


def test_invalid_json_returns_empty():
    llm = FakeLLM(responses={"x": "không phải JSON gì cả"})
    facts, ev, events = LLMExtractor(llm).extract("x")
    assert facts == {} and events == []
