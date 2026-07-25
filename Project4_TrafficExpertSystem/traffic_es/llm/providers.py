from __future__ import annotations

import os
from typing import Optional, Tuple

from traffic_es.llm.client import LLMClient


class OpenAILLM(LLMClient):
    """Provider OpenAI. Import `openai` trễ để test/heuristic không cần thư viện."""

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        from openai import OpenAI

        self.model = model or os.environ.get("TRAFFIC_ES_LLM_MODEL", "gpt-4o-mini")
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def complete(self, system: str, user: str, **kw) -> str:
        r = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        return r.choices[0].message.content or ""


class AnthropicLLM(LLMClient):
    """Provider Anthropic (Claude). Dùng Messages API; import `anthropic` trễ."""

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        import anthropic

        # Mặc định Opus 4.8; đổi rẻ hơn bằng TRAFFIC_ES_LLM_MODEL=claude-haiku-4-5
        self.model = model or os.environ.get("TRAFFIC_ES_LLM_MODEL", "claude-opus-4-8")
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )

    def complete(self, system: str, user: str, **kw) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system + "\nChỉ trả về JSON hợp lệ, không kèm giải thích.",
            messages=[{"role": "user", "content": user}],
        )
        # Lấy khối text đầu tiên (Opus 4.8 không kèm thinking khi bỏ tham số thinking)
        for block in msg.content:
            if getattr(block, "type", None) == "text":
                return block.text
        return ""


def make_default_llm() -> Optional[LLMClient]:
    """Chọn LLMClient theo môi trường; None nếu không có key (→ dùng heuristic).

    Ưu tiên theo TRAFFIC_ES_LLM_PROVIDER (anthropic|openai) nếu đặt; ngược lại
    dùng key nào có sẵn (Anthropic trước, rồi OpenAI).
    """
    provider = os.environ.get("TRAFFIC_ES_LLM_PROVIDER", "").strip().lower()
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))

    order: Tuple[str, ...]
    if provider == "anthropic":
        order = ("anthropic",)
    elif provider == "openai":
        order = ("openai",)
    else:
        order = ("anthropic", "openai")

    for name in order:
        try:
            if name == "anthropic" and has_anthropic:
                return AnthropicLLM()
            if name == "openai" and has_openai:
                return OpenAILLM()
        except Exception:
            continue
    return None


def default_mode_label() -> str:
    """Nhãn chế độ để hiển thị trên UI (không khởi tạo client)."""
    provider = os.environ.get("TRAFFIC_ES_LLM_PROVIDER", "").strip().lower()
    if (provider == "anthropic" or not provider) and os.environ.get("ANTHROPIC_API_KEY"):
        model = os.environ.get("TRAFFIC_ES_LLM_MODEL", "claude-opus-4-8")
        return f"LLM (Anthropic · {model})"
    if os.environ.get("OPENAI_API_KEY"):
        model = os.environ.get("TRAFFIC_ES_LLM_MODEL", "gpt-4o-mini")
        return f"LLM (OpenAI · {model})"
    return "Heuristic offline"
