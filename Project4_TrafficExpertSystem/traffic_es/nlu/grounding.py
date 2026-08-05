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

_KNOWN_PREFIX = (
    "phuongtien.",
    "nguoi.",
    "chiso.",
    "boicanh.",
    "tinhtiet.",
    "hanhvi.",
    "giayto.",
)


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
    "phuongtien.loai": _enum("o_to", "xe_may", "xe_dap"),
    # ── Người điều khiển ──
    "nguoi.coGPLX": Slot(BOOL),
    "nguoi.khong_mu_bao_hiem": Slot(BOOL),
    "nguoi.khong_day_an_toan": Slot(BOOL),
    "nguoi.co_chat_ma_tuy": Slot(BOOL),
    "nguoi.chua_du_tuoi_lai_xe": Slot(BOOL),
    "nguoi.gplx_khong_dung_tham_quyen": Slot(BOOL),
    # ── Chỉ số đo lường ──
    "chiso.nongDoCon_khiTho": _num(0.0, 5.0, "mg/l"),
    "chiso.nongDoCon_mau": _num(0.0, 500.0, "mg/100ml"),
    "chiso.tocDo": _num(0.0, 300.0, "km/h"),
    "chiso.tocDoGioiHan": _num(0.0, 150.0, "km/h"),
    "chiso.vuot_toc_do_kmh": _num(-300.0, 300.0, "km/h"),
    "chiso.vuot_toc_do_pct": _num(-100.0, 1000.0, "%"),
    "chiso.ty_le_qua_tai": _num(0.0, 500.0, "%"),
    "chiso.so_nguoi_vuot": _num(0.0, 200.0, "nguoi"),
    # ── Bối cảnh ──
    "boicanh.khuVuc": _enum("khu_dan_cu", "do_thi", "ngoai_do_thi", "cao_toc"),
    "boicanh.thoiDiem": _enum("ban_ngay", "ban_dem"),
    "boicanh.vi_tri_cam_do": Slot(BOOL),
    # ── Giấy tờ ──
    "giayto.khong_co_dang_ky_xe": Slot(BOOL),
    "giayto.khong_mang_dang_ky_xe": Slot(BOOL),
    "giayto.khong_mang_dang_kiem": Slot(BOOL),
    "giayto.het_han_dang_kiem": Slot(BOOL),
    # ── Hành vi ──
    "hanhvi.vuot_den_do": Slot(BOOL),
    "hanhvi.vuot_den_vang": Slot(BOOL),
    "hanhvi.khong_chap_hanh_csgt": Slot(BOOL),
    "hanhvi.cam_dien_thoai": Slot(BOOL),
    "hanhvi.su_dung_thiet_bi_am_thanh": Slot(BOOL),
    "hanhvi.sai_lan": Slot(BOOL),
    "hanhvi.sai_phan_duong": Slot(BOOL),
    "hanhvi.chuyen_lan_khong_tin_hieu": Slot(BOOL),
    "hanhvi.quay_dau_cam": Slot(BOOL),
    "hanhvi.vuot_cam": Slot(BOOL),
    "hanhvi.nguoc_chieu": Slot(BOOL),
    "hanhvi.dung_do_sai": Slot(BOOL),
    "hanhvi.bien_so_gia": Slot(BOOL),
    "hanhvi.che_bien_so": Slot(BOOL),
    "hanhvi.sua_bien_so": Slot(BOOL),
    "hanhvi.cho_qua_tai": Slot(BOOL),
    "hanhvi.cho_qua_kho": Slot(BOOL),
    "hanhvi.cho_qua_so_nguoi": Slot(BOOL),
    "hanhvi.don_tra_khach_sai": Slot(BOOL),
    "hanhvi.thu_tien_qua_gia_ve": Slot(BOOL),
    "hanhvi.hanh_khach_gay_roi": Slot(BOOL),
    "hanhvi.hanh_khach_du_bam": Slot(BOOL),
    "hanhvi.hanh_khach_mo_cua_khi_xe_chay": Slot(BOOL),
    "hanhvi.nguoi_di_bo_sai_phan_duong": Slot(BOOL),
    "hanhvi.vuot_dai_phan_cach": Slot(BOOL),
    "hanhvi.nguoi_di_bo_khong_chap_hanh_den": Slot(BOOL),
    "hanhvi.giao_xe_nguoi_khong_du_dk": Slot(BOOL),
    "hanhvi.thay_doi_may_khung": Slot(BOOL),
    "hanhvi.thay_doi_mau_son_trai_quy_dinh": Slot(BOOL),
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
