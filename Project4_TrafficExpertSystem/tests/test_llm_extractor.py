import json

from traffic_es.llm.client import FakeLLM
from traffic_es.nlu.llm_extractor import LLMExtractor


def test_llm_extractor_maps_facts():
    llm = FakeLLM(
        responses={
            "ô tô": json.dumps(
                {
                    "facts": {
                        "phuongtien.loai": {"value": "o_to", "nguon": "lái ô tô"},
                        "chiso.nongDoCon_khiTho": {"value": 0.42, "nguon": "cồn 0.42"},
                    },
                    "raw_events": ["đâm vào xe máy"],
                }
            )
        }
    )
    facts, ev, raw = LLMExtractor(llm).extract("lái ô tô cồn 0.42 đâm vào xe máy")
    assert facts["phuongtien.loai"] == "o_to"
    assert ev["phuongtien.loai"] == "lái ô tô"
    assert "đâm vào xe máy" in raw
