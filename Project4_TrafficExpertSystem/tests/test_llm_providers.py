import traffic_es.llm.providers as prov


def _clear(monkeypatch):
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "TRAFFIC_ES_LLM_PROVIDER"):
        monkeypatch.delenv(k, raising=False)


def test_make_default_none_without_key(monkeypatch):
    _clear(monkeypatch)
    assert prov.make_default_llm() is None
    assert prov.default_mode_label() == "Heuristic offline"


def test_make_default_returns_openai_with_key(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    llm = prov.make_default_llm()
    assert isinstance(llm, prov.OpenAILLM)
    assert "OpenAI" in prov.default_mode_label()


def test_make_default_prefers_anthropic(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    llm = prov.make_default_llm()
    assert isinstance(llm, prov.AnthropicLLM)
    assert "Anthropic" in prov.default_mode_label()


def test_provider_override_forces_openai(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("TRAFFIC_ES_LLM_PROVIDER", "openai")
    assert isinstance(prov.make_default_llm(), prov.OpenAILLM)
