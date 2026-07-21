from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from traffic_es.engine.reasoner import Reasoner, InferResult
from traffic_es.nlu.pipeline import NLUPipeline
from traffic_es.explain.generator import render_explanation
from traffic_es.engine.penalty import KetQua
from traffic_es.engine.trace import Trace


@dataclass
class Answer:
    ket_qua: KetQua
    trace: Trace
    explanation: str
    facts: Dict[str, Any]
    nlu_meta: Dict[str, Any]


class TrafficESService:
    def __init__(self, reasoner: Reasoner, nlu: NLUPipeline):
        self.reasoner = reasoner
        self.nlu = nlu

    @classmethod
    def default(cls, rules_dir: Path) -> "TrafficESService":
        return cls(Reasoner.from_rules_dir(rules_dir), NLUPipeline())

    def answer(self, text: str) -> Answer:
        facts, meta = self.nlu.run(text)
        res: InferResult = self.reasoner.infer(facts)
        explanation = render_explanation(res.trace, res.ket_qua)
        return Answer(res.ket_qua, res.trace, explanation, facts, meta)
