from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.engine.trace import Trace
from traffic_es.engine.funcs import Func, DEFAULT_FUNCS
from traffic_es.engine.deduction_network import solve_and_apply
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
        # Deduce_Objects qua mạng (M,R) + A*; Goal gồm cả thuộc tính meta-rule cần
        solve_and_apply(wm, self.funcs, self.rules, trace, self.meta_rules)
        fired = deduce_rules(wm, self.rules, trace)  # Deduce_Rules
        picks = apply_meta(wm, self.meta_rules, trace, fired)  # Meta-rule theo từng lỗi
        ket_qua = aggregate(fired, picks)  # Gộp phạt
        trace.add(
            "KL",
            f"Tổng {len(fired)} lỗi; tổng tiền {ket_qua.tong_tien}",
            {"so_loi": len(fired), "tong_tien": ket_qua.tong_tien},
        )
        return InferResult(ket_qua, trace, wm.as_dict())
