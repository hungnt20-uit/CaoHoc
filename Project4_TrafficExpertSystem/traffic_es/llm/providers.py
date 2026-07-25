from __future__ import annotations

import os
from typing import Optional

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


def make_default_llm() -> Optional[LLMClient]:
    """Trả LLMClient theo biến môi trường; None nếu không có key (→ dùng heuristic)."""
    if not os.environ.get("OPENAI_API_KEY"):
        return None
    try:
        return OpenAILLM()
    except Exception:
        return None
