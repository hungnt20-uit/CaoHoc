from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional


class LLMClient:
    """Giao diện LLM tối thiểu. Provider thật kế thừa và override complete()."""

    def complete(self, system: str, user: str, **kw: Any) -> str:
        raise NotImplementedError

    def complete_json(self, system: str, user: str, **kw: Any) -> Dict[str, Any]:
        raw = self.complete(system=system, user=user, **kw)
        return json.loads(raw)


class FakeLLM(LLMClient):
    """LLM giả cho test: khớp 'user' với substring trong responses."""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        self.responses = responses or {}

    def complete(self, system: str, user: str, **kw: Any) -> str:
        for key, val in self.responses.items():
            if key in user:
                return val
        return ""


class CachingLLM(LLMClient):
    """Bọc một LLMClient, cache theo hash (system, user)."""

    def __init__(self, inner: LLMClient):
        self.inner = inner
        self._cache: Dict[str, str] = {}

    def _key(self, system: str, user: str) -> str:
        return hashlib.sha256((system + "\x00" + user).encode("utf-8")).hexdigest()

    def complete(self, system: str, user: str, **kw: Any) -> str:
        k = self._key(system, user)
        if k not in self._cache:
            self._cache[k] = self.inner.complete(system=system, user=user, **kw)
        return self._cache[k]
