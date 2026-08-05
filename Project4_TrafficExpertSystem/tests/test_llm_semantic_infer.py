from traffic_es.llm.client import FakeLLM, LLMClient
from traffic_es.nlu.llm_semantic_infer import LLMCircumstanceInferrer, validate
from traffic_es.nlu.pipeline import NLUPipeline


class _Boom(LLMClient):
    def complete(self, system: str, user: str, **kw):
        raise RuntimeError("hết quota")


def test_llm_infers_paraphrased_event():
    llm = FakeLLM({
        "hạ gục cái gương": (
            '{"tinh_tiet": [{"fact": "tinhtiet.gay_tai_nan", "value": true, '
            '"confidence": 0.85, "ly_do": "làm hỏng gương xe khác", '
            '"nguon": "hạ gục cái gương"}]}'
        )
    })
    out = LLMCircumstanceInferrer(llm).infer(["xe tôi hạ gục cái gương của người ta"])
    assert out[0]["fact"] == "tinhtiet.gay_tai_nan"
    assert out[0]["confidence"] == 0.85
    assert out[0]["bo_suy_luan"] == "llm"


def test_rejects_fact_outside_closed_vocabulary():
    assert validate([{"fact": "tinhtiet.bay_len_troi", "value": True, "confidence": 0.9}]) == []


def test_rejects_bad_confidence_and_non_boolean():
    assert validate([{"fact": "tinhtiet.tai_pham", "value": True, "confidence": 7}]) == []
    assert validate([{"fact": "tinhtiet.tai_pham", "value": "có", "confidence": 0.9}]) == []


def test_falls_back_to_keyword_when_llm_returns_nothing():
    out = LLMCircumstanceInferrer(FakeLLM({})).infer(["quẹt trúng một xe máy"])
    assert out[0]["fact"] == "tinhtiet.gay_tai_nan"
    assert out[0]["bo_suy_luan"] == "keyword"


def test_falls_back_when_llm_raises():
    out = LLMCircumstanceInferrer(_Boom()).infer(["đây là lần tái phạm"])
    assert out[0]["fact"] == "tinhtiet.tai_pham"


def test_low_confidence_is_flagged_for_confirmation():
    llm = FakeLLM({
        "có lẽ va vào": (
            '{"tinh_tiet": [{"fact": "tinhtiet.gay_tai_nan", "value": true, '
            '"confidence": 0.35, "ly_do": "mô tả mơ hồ", "nguon": "có lẽ va vào"}]}'
        )
    })
    pipeline = NLUPipeline(inferrer=LLMCircumstanceInferrer(llm))
    _facts, meta = pipeline.run("Tôi đi xe máy, có lẽ va vào xe bên cạnh")
    assert "tinhtiet.gay_tai_nan" in meta["can_xac_nhan"]
    assert any("cần xác nhận" in w for w in meta["warnings"])
