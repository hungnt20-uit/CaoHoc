from traffic_es.llm.client import FakeLLM, CachingLLM


def test_fake_llm_returns_scripted():
    llm = FakeLLM(responses={"xin chào": "chào bạn"})
    assert llm.complete(system="s", user="xin chào") == "chào bạn"


def test_fake_llm_json():
    llm = FakeLLM(responses={"trích": '{"a": 1}'})
    assert llm.complete_json(system="s", user="trích") == {"a": 1}


def test_caching_llm_calls_once():
    calls = {"n": 0}

    class Counting(FakeLLM):
        def complete(self, system, user, **kw):
            calls["n"] += 1
            return "x"

    llm = CachingLLM(Counting(responses={}))
    llm.complete(system="s", user="u")
    llm.complete(system="s", user="u")
    assert calls["n"] == 1  # lần 2 lấy từ cache
