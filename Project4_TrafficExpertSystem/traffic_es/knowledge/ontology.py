from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class Concept:
    """Khái niệm Legal-Onto: (Name, Content, InnerRul, Attrs, Keyphrases)."""

    name: str
    content: str = ""
    inner_rul: str = ""
    attrs: Dict[str, str] = field(default_factory=dict)
    keyphrases: List[str] = field(default_factory=list)


@dataclass
class ConceptStore:
    concepts: List[Concept] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path) -> "ConceptStore":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        items = [Concept(**c) for c in raw.get("concepts", [])]
        return cls(items)

    def find_by_keyphrase(self, phrase: str) -> Optional[Concept]:
        p = phrase.strip().lower()
        for c in self.concepts:
            if p == c.name.lower() or any(p == k.lower() for k in c.keyphrases):
                return c
        return None
