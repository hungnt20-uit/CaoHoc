from __future__ import annotations

from typing import Any, Dict, Optional


class WorkingMemory:
    """Bộ nhớ làm việc: map fact-key (dạng 'chiso.tocDo') -> giá trị, kèm nguồn."""

    def __init__(self, facts: Optional[Dict[str, Any]] = None):
        self._facts: Dict[str, Any] = dict(facts or {})
        self._source: Dict[str, str] = {k: "INPUT" for k in self._facts}

    def has(self, key: str) -> bool:
        return key in self._facts

    def get(self, key: str, default: Any = None) -> Any:
        return self._facts.get(key, default)

    def set(self, key: str, value: Any, source: str = "INPUT") -> None:
        self._facts[key] = value
        self._source[key] = source

    def source_of(self, key: str) -> Optional[str]:
        return self._source.get(key)

    def as_dict(self) -> Dict[str, Any]:
        return dict(self._facts)
