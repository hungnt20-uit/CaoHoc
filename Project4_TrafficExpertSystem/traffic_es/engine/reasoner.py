from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.engine.trace import Trace
from traffic_es.engine.funcs import Func, DEFAULT_FUNCS, apply_funcs
from traffic_es.engine.forward_chaining import deduce_rules, apply_meta
from traffic_es.engine.penalty import aggregate, KetQua
from traffic_es.knowledge.rules import Rule, MetaRule
from traffic_es.knowledge.kb_loader import load_kb


@dataclass
class InferResult:
    ket_qua: KetQua
    trace: Trace
    working_memory: Dict[str, Any]


class Reasoner:
    def __init__(
        self,
        rules: List[Rule],
        meta_rules: List[MetaRule],
        funcs: Optional[List[Func]] = None,
    ):
        self.rules = rules
        self.meta_rules = meta_rules
        self.funcs = funcs if funcs is not None else DEFAULT_FUNCS

    @classmethod
    def from_rules_dir(cls, rules_dir: Path) -> "Reasoner":
        rules, meta = load_kb(rules_dir)
        return cls(rules, meta)

    def infer(self, facts: Dict[str, Any]) -> InferResult:
        wm = WorkingMemory(facts)
        trace = Trace()
        apply_funcs(wm, self.funcs, trace)  # Deduce_Objects
        fired = deduce_rules(wm, self.rules, trace)  # Deduce_Rules
        pick = apply_meta(wm, self.meta_rules, trace)  # Meta-rule
        ket_qua = aggregate(fired, pick)  # Gộp phạt
        trace.add(
            "KL",
            f"Tổng {len(fired)} lỗi; tổng tiền {ket_qua.tong_tien}",
            {"so_loi": len(fired), "tong_tien": ket_qua.tong_tien},
        )
        return InferResult(ket_qua, trace, wm.as_dict())
