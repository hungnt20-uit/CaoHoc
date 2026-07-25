import traffic_es.llm.providers as prov


def test_make_default_none_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert prov.make_default_llm() is None


def test_make_default_returns_client_with_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    # không gọi API thật: chỉ kiểm tra tạo được đối tượng có .complete
    llm = prov.make_default_llm()
    assert llm is not None and hasattr(llm, "complete")
