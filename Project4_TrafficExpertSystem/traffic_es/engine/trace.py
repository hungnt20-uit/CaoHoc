from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class TraceStep:
    kind: str  # FUNC | RULE | META | ASTAR | KL
    detail: str
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Trace:
    steps: List[TraceStep] = field(default_factory=list)

    def add(self, kind: str, detail: str, data: Dict[str, Any] | None = None) -> None:
        self.steps.append(TraceStep(kind, detail, dict(data or {})))

    def render(self) -> str:
        return "\n".join(f"[{s.kind:5}] {s.detail}" for s in self.steps)
