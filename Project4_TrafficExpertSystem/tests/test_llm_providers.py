import importlib

import pytest

import traffic_es.llm.providers as prov


def _clear(monkeypatch):
    for k in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "TRAFFIC_ES_LLM_PROVIDER",
        "TRAFFIC_ES_LOCAL_BASE_URL",
        "TRAFFIC_ES_LOCAL_MODEL",
        "TRAFFIC_ES_LOCAL_API_KEY",
    ):
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


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("https://a.trycloudflare.com", "https://a.trycloudflare.com/v1"),
        ("https://a.trycloudflare.com/", "https://a.trycloudflare.com/v1"),
        ("https://a.trycloudflare.com/v1", "https://a.trycloudflare.com/v1"),
        ("https://a.trycloudflare.com/v1/", "https://a.trycloudflare.com/v1"),
        ("a.trycloudflare.com", "https://a.trycloudflare.com/v1"),
        ("  https://a.trycloudflare.com  ", "https://a.trycloudflare.com/v1"),
        ("http://localhost:8000", "http://localhost:8000/v1"),
        # Máy cục bộ không có TLS: đoán https sẽ vỡ bắt tay SSL.
        ("localhost:8000", "http://localhost:8000/v1"),
        ("127.0.0.1:8000/v1", "http://127.0.0.1:8000/v1"),
        (
            "https://a.trycloudflare.com/v1/chat/completions",
            "https://a.trycloudflare.com/v1",
        ),
        ("", ""),
    ],
)
def test_normalize_base_url_accepts_what_users_actually_paste(raw, expected):
    assert prov.normalize_base_url(raw) == expected


def test_local_provider_selected_by_explicit_provider(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("TRAFFIC_ES_LLM_PROVIDER", "local")
    llm = prov.make_default_llm()
    assert isinstance(llm, prov.LocalOpenAICompatLLM)
    assert llm.model is None  # chưa chỉ định -> để resolved_model() tự dò
    assert "local" in prov.default_mode_label()


def test_local_used_as_last_resort_when_no_cloud_key(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("TRAFFIC_ES_LOCAL_BASE_URL", "https://a.trycloudflare.com")
    llm = prov.make_default_llm()
    assert isinstance(llm, prov.LocalOpenAICompatLLM)
    assert llm.base_url == "https://a.trycloudflare.com/v1"
    assert "local" in prov.default_mode_label()


def test_cloud_key_wins_over_local_in_auto_mode(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("TRAFFIC_ES_LOCAL_BASE_URL", "https://a.trycloudflare.com")
    assert isinstance(prov.make_default_llm(), prov.OpenAILLM)
    assert "OpenAI" in prov.default_mode_label()


def test_local_complete_sends_json_instruction_and_no_response_format(monkeypatch):
    """Server tự dựng thường từ chối `response_format`, nên yêu cầu JSON phải nằm ở prompt."""
    _clear(monkeypatch)
    llm = prov.LocalOpenAICompatLLM(base_url="http://localhost:1/v1", model="qwen")
    seen = {}

    def fake_create(**kw):
        seen.update(kw)

        class _Msg:
            content = '{"ok": true}'

        return type("R", (), {"choices": [type("C", (), {"message": _Msg()})()]})()

    monkeypatch.setattr(llm.client.chat.completions, "create", fake_create)

    assert llm.complete(system="Trích xuất.", user="xe máy") == '{"ok": true}'
    assert "response_format" not in seen
    assert seen["temperature"] == 0
    assert seen["model"] == "qwen"
    assert "JSON" in seen["messages"][0]["content"]


def _stub_served(monkeypatch, llm, ids):
    monkeypatch.setattr(
        llm.client.models,
        "list",
        lambda: type("L", (), {"data": [type("M", (), {"id": i})() for i in ids]})(),
    )


def test_model_name_discovered_from_server_when_left_blank(monkeypatch):
    """vLLM phục vụ dưới bí danh (`coder-7b`), đoán tên đầy đủ sẽ dính 404."""
    _clear(monkeypatch)
    llm = prov.LocalOpenAICompatLLM(base_url="http://localhost:1/v1")
    _stub_served(monkeypatch, llm, ["coder-7b"])
    assert llm.resolved_model() == "coder-7b"


def test_explicit_model_is_not_overridden_by_discovery(monkeypatch):
    _clear(monkeypatch)
    llm = prov.LocalOpenAICompatLLM(base_url="http://localhost:1/v1", model="của-tôi")
    _stub_served(monkeypatch, llm, ["coder-7b"])
    assert llm.resolved_model() == "của-tôi"


def test_discovery_falls_back_to_default_when_server_unreachable(monkeypatch):
    _clear(monkeypatch)
    llm = prov.LocalOpenAICompatLLM(base_url="http://localhost:1/v1")

    def boom():
        raise ConnectionError("tắt rồi")

    monkeypatch.setattr(llm.client.models, "list", boom)
    assert llm.resolved_model() == prov.DEFAULT_LOCAL_MODEL


def test_health_flags_model_name_mismatch(monkeypatch):
    _clear(monkeypatch)
    llm = prov.LocalOpenAICompatLLM(
        base_url="http://localhost:1/v1", model="Qwen/Qwen2.5-Coder-7B-Instruct"
    )
    _stub_served(monkeypatch, llm, ["coder-7b"])
    ok, msg = llm.health()
    assert ok is False
    assert "coder-7b" in msg


def test_local_health_reports_failure_instead_of_raising(monkeypatch):
    _clear(monkeypatch)
    llm = prov.LocalOpenAICompatLLM(base_url="http://localhost:1/v1")

    def boom():
        raise ConnectionError("khong ket noi duoc")

    monkeypatch.setattr(llm.client.models, "list", boom)

    ok, msg = llm.health()
    assert ok is False
    assert "khong ket noi duoc" in msg


def test_loads_anthropic_from_dotenv_file(monkeypatch, tmp_path):
    _clear(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ANTHROPIC_API_KEY=sk-ant-test\nTRAFFIC_ES_LLM_PROVIDER=anthropic\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    importlib.reload(prov)
    assert isinstance(prov.make_default_llm(), prov.AnthropicLLM)
