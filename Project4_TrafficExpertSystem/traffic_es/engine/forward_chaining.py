from __future__ import annotations

from typing import Dict, List, Optional, Union

from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.engine.trace import Trace
from traffic_es.engine.conditions import eval_cond_node
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
        if all(eval_cond_node(c, wm) for c in r.dieu_kien):
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
    wm: WorkingMemory,
    meta_rules: List[MetaRule],
    trace: Trace,
    fired: Optional[List[Rule]] = None,
) -> Union[Optional[str], Dict[str, Optional[str]]]:
    """Áp meta-rule tình tiết cho TỪNG lỗi đã khớp.

    Trả về map `rule_id -> 'max'|'min'|None` khi có `fired`; nếu không truyền `fired`
    thì suy biến về một mức chọn chung (giữ tương thích cho các phép thử đơn vị).

    Khi một lỗi vừa có tình tiết tăng nặng lẫn giảm nhẹ, hai bên **bù trừ** về mức
    trung bình của khung — quyết định không phụ thuộc thứ tự dòng trong file YAML.
    """
    matched = [m for m in meta_rules if all(eval_cond_node(c, wm) for c in m.dieu_kien)]
    for m in matched:
        pham_vi = ", ".join(m.ap_dung_nhom) if m.ap_dung_nhom else "mọi lỗi"
        trace.add(
            "META",
            f"{m.id} ({pham_vi}): {m.ghi_chu or ''}".strip(),
            {"meta_id": m.id, "chon_muc": m.chon_muc, "ap_dung_nhom": m.ap_dung_nhom},
        )

    if fired is None:
        return _resolve([m.chon_muc for m in matched], trace, None)

    picks: Dict[str, Optional[str]] = {}
    for r in fired:
        mucs = [m.chon_muc for m in matched if m.ap_dung_cho(r.nhom)]
        picks[r.id] = _resolve(mucs, trace, r.id)
    return picks


def _resolve(
    mucs: List[Optional[str]], trace: Trace, rule_id: Optional[str]
) -> Optional[str]:
    """Quy tắc hợp giải xung đột tình tiết (độc lập thứ tự khai báo)."""
    has_max = "max" in mucs
    has_min = "min" in mucs
    if has_max and has_min:
        trace.add(
            "META",
            (f"{rule_id}: " if rule_id else "")
            + "có cả tình tiết tăng nặng và giảm nhẹ → bù trừ, áp mức trung bình khung",
            {"rule_id": rule_id, "chon_muc": None, "bu_tru": True},
        )
        return None
    if has_max:
        return "max"
    if has_min:
        return "min"
    return None
