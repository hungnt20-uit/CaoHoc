from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from traffic_es.engine.reasoner import Reasoner, InferResult
from traffic_es.nlu.pipeline import NLUPipeline
from traffic_es.nlu.clarify import (
    ClarifyingQuestion,
    needed_clarifications,
    enrich_pending_from_hints,
    VEHICLE_FIELD,
    BEHAVIOR_FIELD,
    _strip_clarify_keys,
)
from traffic_es.explain.generator import render_explanation
from traffic_es.engine.penalty import KetQua
from traffic_es.engine.trace import Trace
from traffic_es.knowledge.sample_problems import best_problem, SampleProblem


@dataclass
class Answer:
    ket_qua: KetQua
    trace: Trace
    explanation: str
    facts: Dict[str, Any]
    nlu_meta: Dict[str, Any]
    sample_problem: Optional[SampleProblem] = None
    clarifications: List[ClarifyingQuestion] = field(default_factory=list)


class TrafficESService:
    def __init__(self, reasoner: Reasoner, nlu: NLUPipeline):
        self.reasoner = reasoner
        self.nlu = nlu

    @classmethod
    def default(cls, rules_dir: Path) -> "TrafficESService":
        return cls(Reasoner.from_rules_dir(rules_dir), NLUPipeline())

    def answer(self, text: str) -> Answer:
        facts, meta = self.nlu.run(text)
        facts = enrich_pending_from_hints(facts, meta)
        return self._answer_from_facts(facts, meta)

    def continue_with(self, facts: Mapping[str, Any], meta: Optional[Dict[str, Any]] = None) -> Answer:
        """Suy diễn lại từ facts đã có (sau khi user bổ sung slot thiếu, không chạy NLU)."""
        return self._answer_from_facts(dict(facts), dict(meta or {}))

    def _answer_from_facts(self, facts: Dict[str, Any], meta: Dict[str, Any]) -> Answer:
        clarifications = needed_clarifications(facts, self.reasoner.rules)
        warns = [w for w in (meta.get("warnings") or []) if "Cần bổ sung " not in w]
        if clarifications:
            for q in clarifications:
                msg = f"Cần bổ sung {q.field}: {q.prompt}"
                if msg not in warns:
                    warns.append(msg)
        meta = {**meta, "warnings": warns}

        clean_facts = _strip_clarify_keys(facts)
        res: InferResult = self.reasoner.infer(clean_facts)
        explanation = render_explanation(
            res.trace,
            res.ket_qua,
            missing_vehicle=any(q.field == VEHICLE_FIELD for q in clarifications),
            missing_behavior=any(q.field == BEHAVIOR_FIELD for q in clarifications),
            missing_level=any(
                q.id in ("ask_nong_do_con_muc", "ask_vuot_toc_do_muc")
                for q in clarifications
            ),
        )
        problem = best_problem(clean_facts)
        return Answer(
            res.ket_qua,
            res.trace,
            explanation,
            facts,  # giữ clarify.pending để hỏi khung mức ở bước sau
            meta,
            problem,
            clarifications,
        )
