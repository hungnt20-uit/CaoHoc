from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

from traffic_es.service import TrafficESService
from traffic_es.nlu.pipeline import NLUPipeline
from traffic_es.engine.reasoner import Reasoner
from eval.dataset import Case
from eval.metrics import slot_prf, set_match


def evaluate(cases: List[Case], rules_dir: Path) -> Dict[str, Any]:
    svc = TrafficESService(Reasoner.from_rules_dir(rules_dir), NLUPipeline())
    per: List[Dict[str, Any]] = []
    for c in cases:
        t0 = time.perf_counter()
        facts, meta = svc.nlu.run(c.text)
        t1 = time.perf_counter()
        res = svc.reasoner.infer(facts)
        t2 = time.perf_counter()
        fired = [s.data.get("rule_id") for s in res.trace.steps if s.kind == "RULE"]
        p, r, f = slot_prf(facts, c.expected.get("facts", {}))
        per.append(
            {
                "id": c.id,
                "fired": fired,
                "conclusion": set_match(fired, c.expected.get("rule_ids", [])),
                "money_ok": 1.0
                if res.ket_qua.tong_tien == c.expected.get("tong_tien")
                else 0.0,
                "slot_p": p,
                "slot_r": r,
                "slot_f": f,
                "t_nlu_ms": (t1 - t0) * 1000,
                "t_engine_ms": (t2 - t1) * 1000,
            }
        )
    n = len(per) or 1

    def agg(k: str) -> float:
        return sum(x[k] for x in per) / n

    return {
        "n": len(per),
        "conclusion_acc": agg("conclusion"),
        "money_acc": agg("money_ok"),
        "slot_f1": agg("slot_f"),
        "slot_p": agg("slot_p"),
        "slot_r": agg("slot_r"),
        "avg_t_nlu_ms": agg("t_nlu_ms"),
        "avg_t_engine_ms": agg("t_engine_ms"),
        "per_case": per,
    }
