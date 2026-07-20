from __future__ import annotations

from typing import List, Optional

from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.engine.trace import Trace
from traffic_es.engine.conditions import eval_condition
from traffic_es.knowledge.rules import Rule, MetaRule


def _vehicle_ok(rule: Rule, wm: WorkingMemory) -> bool:
    if not rule.ap_dung_loai_xe:
        return True
    return wm.get("phuongtien.loai") in rule.ap_dung_loai_xe


def deduce_rules(wm: WorkingMemory, rules: List[Rule], trace: Trace) -> List[Rule]:
    """Forward chaining: trả về các luật vi phạm khớp WorkingMemory."""
    fired: List[Rule] = []
    for r in rules:
        if not _vehicle_ok(r, wm):
            continue
        if all(eval_condition(c, wm) for c in r.dieu_kien):
            fired.append(r)
            cc = r.ket_luan.can_cu
            trace.add(
                "RULE",
                f"{r.id} khớp → {r.ket_luan.hanh_vi}",
                {
                    "rule_id": r.id,
                    "can_cu": cc.model_dump(),
                    "tien": [r.ket_luan.tien_phat_min, r.ket_luan.tien_phat_max],
                },
            )
    return fired


def apply_meta(
    wm: WorkingMemory, meta_rules: List[MetaRule], trace: Trace
) -> Optional[str]:
    """Trả về mức chọn 'max'/'min' nếu có meta-rule tình tiết khớp, ngược lại None."""
    pick: Optional[str] = None
    for m in meta_rules:
        if all(eval_condition(c, wm) for c in m.dieu_kien):
            pick = m.chon_muc or pick
            trace.add(
                "META",
                f"{m.id}: {m.ghi_chu or ''}".strip(),
                {"meta_id": m.id, "chon_muc": m.chon_muc},
            )
    return pick
