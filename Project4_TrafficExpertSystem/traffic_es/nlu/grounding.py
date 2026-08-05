"""Validator ontology (grounding) — "LLM đề xuất, ontology phê duyệt".

Đây là lớp chống ảo giác pháp lý duy nhất giữa bộ trích xuất (kể cả LLM) và engine,
nên nó kiểm đủ bốn thứ mà đặc tả yêu cầu: **tên node**, **kiểu dữ liệu**, **đơn vị**
và **miền giá trị**. Chỉ kiểm tiền tố tên node là không đủ: `chiso.tocDo = "abc"` hay
`phuongtien.loai = "xe_tang"` sẽ lọt xuống engine và cho ra mức phạt vô nghĩa.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple

from traffic_es.nlu.semantic_infer import CLOSED_VOCAB

NUMBER = "number"
BOOL = "bool"
ENUM = "enum"

_KNOWN_PREFIX = ("phuongtien.", "nguoi.", "chiso.", "boicanh.", "tinhtiet.", "hanhvi.")


@dataclass(frozen=True)
class Slot:
    """Khai báo một node ontology: kiểu, miền giá trị, đơn vị."""

    kind: str
    rng: Optional[Tuple[float, float]] = None
    domain: Optional[FrozenSet[str]] = None
    unit: Optional[str] = None


def _num(lo: float, hi: float, unit: Optional[str] = None) -> Slot:
    return Slot(NUMBER, rng=(lo, hi), unit=unit)


def _enum(*values: str) -> Slot:
    return Slot(ENUM, domain=frozenset(values))


SCHEMA: Dict[str, Slot] = {
    # ── Phương tiện ──
    "phuongtien.loai": _enum("o_to", "xe_may"),
    # ── Người điều khiển ──
    "nguoi.coGPLX": Slot(BOOL),
    "nguoi.khong_mu_bao_hiem": Slot(BOOL),
    "nguoi.khong_day_an_toan": Slot(BOOL),
    # ── Chỉ số đo lường ──
    "chiso.nongDoCon_khiTho": _num(0.0, 5.0, "mg/l"),
    "chiso.nongDoCon_mau": _num(0.0, 500.0, "mg/100ml"),
    "chiso.tocDo": _num(0.0, 300.0, "km/h"),
    "chiso.tocDoGioiHan": _num(0.0, 150.0, "km/h"),
    "chiso.vuot_toc_do_kmh": _num(-300.0, 300.0, "km/h"),
    "chiso.vuot_toc_do_pct": _num(-100.0, 1000.0, "%"),
    # ── Bối cảnh ──
    "boicanh.khuVuc": _enum("khu_dan_cu", "do_thi", "ngoai_do_thi", "cao_toc"),
    "boicanh.thoiDiem": _enum("ban_ngay", "ban_dem"),
    # ── Hành vi ──
    "hanhvi.vuot_den_do": Slot(BOOL),
}

# Tình tiết lấy trực tiếp từ closed vocabulary của Bài toán 1 để không bị lệch nhau.
SCHEMA.update({tt.fact: Slot(BOOL) for tt in CLOSED_VOCAB})


def _check(key: str, value: object, slot: Slot) -> Optional[str]:
    """Trả về thông điệp lỗi nếu giá trị không hợp lệ, None nếu hợp lệ."""
    if slot.kind == BOOL:
        if not isinstance(value, bool):
            return f"{key}={value!r} sai kiểu (cần boolean) → loại"
        return None
    if slot.kind == ENUM:
        if not isinstance(value, str):
            return f"{key}={value!r} sai kiểu (cần chuỗi) → loại"
        if slot.domain is not None and value not in slot.domain:
            allowed = ", ".join(sorted(slot.domain))
            return f"{key}={value!r} ngoài miền giá trị {{{allowed}}} → loại"
        return None
    # NUMBER — bool là subclass của int trong Python nên phải loại riêng
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        unit = f" {slot.unit}" if slot.unit else ""
        return f"{key}={value!r} sai kiểu (cần số{unit}) → loại"
    if slot.rng is not None:
        lo, hi = slot.rng
        if not (lo <= value <= hi):
            unit = f" {slot.unit}" if slot.unit else ""
            return f"{key}={value}{unit} ngoài miền [{lo},{hi}] → loại"
    return None


def ground(facts: Dict[str, object]) -> Tuple[Dict[str, object], List[str]]:
    """Lọc facts theo ontology, trả về (facts hợp lệ, cảnh báo)."""
    clean: Dict[str, object] = {}
    warns: List[str] = []
    for k, v in facts.items():
        if not k.startswith(_KNOWN_PREFIX):
            warns.append(f"Bỏ node lạ ngoài ontology: {k}")
            continue
        slot = SCHEMA.get(k)
        if slot is None:
            warns.append(f"Node {k} chưa khai báo trong ontology → giữ nhưng không kiểm")
            clean[k] = v
            continue
        err = _check(k, v, slot)
        if err:
            warns.append(err)
            continue
        clean[k] = v
    return clean, warns
