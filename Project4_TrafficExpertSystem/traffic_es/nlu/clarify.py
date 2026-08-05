from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import yaml

from traffic_es.engine.conditions import eval_cond_node
from traffic_es.engine.working_memory import WorkingMemory
from traffic_es.knowledge.rules import Rule

VEHICLE_FIELD = "phuongtien.loai"
BEHAVIOR_FIELD = "clarify.hanh_vi"
PENDING_FIELD = "clarify.pending"

_CLARIFY_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "clarify.yaml"

# Nhóm đo lường trong concepts.yaml — khớp KG thì hỏi khung mức.
_TOPIC_PENDING = {
    "nong_do_con": "nong_do_con",
    "toc_do": "toc_do",
}


def _band_label(raw: Mapping[str, Any]) -> str:
    label = str(raw.get("label") or "")
    example = raw.get("example")
    if example:
        return f"{label} (ví dụ: {example})"
    return label


def _load_clarify_config(path: Path = _CLARIFY_PATH) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _parse_bands(section: Mapping[str, Any]) -> Dict[str, Tuple[str, Dict[str, Any]]]:
    out: Dict[str, Tuple[str, Dict[str, Any]]] = {}
    for key, raw in (section or {}).items():
        facts = dict(raw.get("facts") or {})
        out[str(key)] = (_band_label(raw), facts)
    return out


def _parse_behaviors(
    section: Mapping[str, Any],
) -> Dict[str, Tuple[str, Dict[str, Any]]]:
    out: Dict[str, Tuple[str, Dict[str, Any]]] = {}
    for key, raw in (section or {}).items():
        patch = dict(raw.get("facts") or {})
        pending = raw.get("pending")
        if pending:
            patch[PENDING_FIELD] = pending
        out[str(key)] = (str(raw.get("label") or key), patch)
    return out


_CFG = _load_clarify_config()
VEHICLE_CHOICES: Dict[str, str] = {
    str(k): str(v) for k, v in (_CFG.get("vehicle_choices") or {}).items()
}
_PROMPTS: Dict[str, str] = {
    str(k): str(v) for k, v in (_CFG.get("prompts") or {}).items()
}
ALCOHOL_BANDS = _parse_bands(_CFG.get("alcohol_bands") or {})
SPEED_BANDS = _parse_bands(_CFG.get("speed_bands") or {})
BEHAVIOR_SPECS = _parse_behaviors(_CFG.get("behaviors") or {})


@dataclass(frozen=True)
class ClarifyingQuestion:
    id: str
    field: str
    prompt: str
    choices: Mapping[str, str]  # value -> nhãn hiển thị
    # value -> facts merge khi chọn (mặc định {field: value} nếu trống)
    patches: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)


_VEHICLE_QUESTION = ClarifyingQuestion(
    id="ask_phuongtien_loai",
    field=VEHICLE_FIELD,
    prompt=_PROMPTS.get(
        "vehicle",
        "Bạn đang điều khiển loại phương tiện nào?",
    ),
    choices=VEHICLE_CHOICES,
)

_BEHAVIOR_QUESTION = ClarifyingQuestion(
    id="ask_hanh_vi",
    field=BEHAVIOR_FIELD,
    prompt=_PROMPTS.get(
        "behavior",
        "Chưa xác định được hành vi vi phạm cụ thể. Bạn đang hỏi về lỗi nào?",
    ),
    choices={k: label for k, (label, _) in BEHAVIOR_SPECS.items()},
    patches={k: patch for k, (_, patch) in BEHAVIOR_SPECS.items()},
)

_ALCOHOL_BAND_QUESTION = ClarifyingQuestion(
    id="ask_nong_do_con_muc",
    field="clarify.nong_do_con_muc",
    prompt=_PROMPTS.get("alcohol_band", "Nồng độ cồn thuộc mức nào?"),
    choices={k: label for k, (label, _) in ALCOHOL_BANDS.items()},
    patches={k: patch for k, (_, patch) in ALCOHOL_BANDS.items()},
)

_SPEED_BAND_QUESTION = ClarifyingQuestion(
    id="ask_vuot_toc_do_muc",
    field="clarify.vuot_toc_do_muc",
    prompt=_PROMPTS.get("speed_band", "Bạn vượt quá tốc độ quy định bao nhiêu?"),
    choices={k: label for k, (label, _) in SPEED_BANDS.items()},
    patches={k: patch for k, (_, patch) in SPEED_BANDS.items()},
)


def enrich_pending_from_hints(
    facts: Mapping[str, Any],
    meta: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Nếu KG đã khớp chủ đề cồn/tốc độ nhưng chưa có số liệu → đặt pending hỏi khung mức.

    Keyphrase nằm trong `concepts.yaml`; khung mức nằm trong `clarify.yaml`.
    """
    out = dict(facts)
    if out.get(PENDING_FIELD):
        return out
    if has_alcohol_measure(out) or has_speed_measure(out):
        return out

    for m in (meta or {}).get("matched_concepts") or []:
        nhom = str(m.get("nhom") or "")
        pending = _TOPIC_PENDING.get(nhom)
        if pending:
            out[PENDING_FIELD] = pending
            return out
    return out


def has_alcohol_measure(facts: Mapping[str, Any]) -> bool:
    return any(k.startswith("chiso.nongDoCon") for k in facts)


def has_speed_measure(facts: Mapping[str, Any]) -> bool:
    return "chiso.vuot_toc_do_kmh" in facts or (
        "chiso.tocDo" in facts and "chiso.tocDoGioiHan" in facts
    )


def _strip_clarify_keys(facts: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in facts.items() if not str(k).startswith("clarify.")}


def _with_derived(facts: Mapping[str, Any]) -> Dict[str, Any]:
    """Bổ sung fact suy ra (vd. vượt tốc độ) để kiểm tra điều kiện luật trước khi infer."""
    out = dict(facts)
    toc = out.get("chiso.tocDo")
    gioi = out.get("chiso.tocDoGioiHan")
    if toc is not None and gioi is not None and "chiso.vuot_toc_do_kmh" not in out:
        out["chiso.vuot_toc_do_kmh"] = float(toc) - float(gioi)
    return out


def _conditions_match_ignoring_vehicle(rule: Rule, wm: WorkingMemory) -> bool:
    """Đánh giá dieu_kien mà không lọc ap_dung_loai_xe."""
    return all(eval_cond_node(c, wm) for c in rule.dieu_kien)


def has_matching_behavior(facts: Mapping[str, Any], rules: Sequence[Rule]) -> bool:
    wm = WorkingMemory(_with_derived(_strip_clarify_keys(dict(facts))))
    return any(
        rule.ap_dung_loai_xe and _conditions_match_ignoring_vehicle(rule, wm)
        for rule in rules
    )


def apply_clarification(
    facts: Mapping[str, Any],
    question: ClarifyingQuestion,
    choice: str,
    extras: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Gộp lựa chọn làm rõ vào facts. `extras` giữ để tương thích, không dùng cho nhập số."""
    out = dict(facts)
    patch = question.patches.get(choice)
    if patch is not None:
        out.update(patch)
    else:
        out[question.field] = choice
    if extras:
        for key, value in extras.items():
            if value is not None and not str(key).startswith("clarify."):
                out[key] = value
    if question.id in ("ask_nong_do_con_muc", "ask_vuot_toc_do_muc"):
        out.pop(PENDING_FIELD, None)
    out.pop(BEHAVIOR_FIELD, None)
    out.pop("clarify.nong_do_con_muc", None)
    out.pop("clarify.vuot_toc_do_muc", None)
    return _with_derived(out)


def needed_clarifications(
    facts: Mapping[str, Any], rules: Sequence[Rule]
) -> List[ClarifyingQuestion]:
    """Một câu hỏi mỗi lần: khung cồn/tốc độ (nếu pending) → hành vi → loại xe."""
    pending = facts.get(PENDING_FIELD)
    if pending == "nong_do_con":
        return [_ALCOHOL_BAND_QUESTION]
    if pending == "toc_do":
        return [_SPEED_BAND_QUESTION]
    if not has_matching_behavior(facts, rules):
        return [_BEHAVIOR_QUESTION]
    if facts.get(VEHICLE_FIELD) not in VEHICLE_CHOICES:
        return [_VEHICLE_QUESTION]
    return []
