from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from traffic_es.knowledge.rules import Rule


@dataclass
class DongPhat:
    hanh_vi: str
    tien: int
    can_cu: str
    phat_bo_sung: str


@dataclass
class KetQua:
    chi_tiet: List[DongPhat] = field(default_factory=list)
    tong_tien: int = 0
    tuoc_gplx_thang_max: Optional[int] = None
    tru_diem_max: Optional[int] = None


def _tien_cua(rule: Rule, pick: Optional[str]) -> int:
    kl = rule.ket_luan
    if pick == "max":
        return kl.tien_phat_max
    if pick == "min":
        return kl.tien_phat_min
    return (kl.tien_phat_min + kl.tien_phat_max) // 2


def _can_cu_str(rule: Rule) -> str:
    c = rule.ket_luan.can_cu
    parts = [f"Điều {c.dieu}"]
    if c.khoan is not None:
        parts.append(f"Khoản {c.khoan}")
    if c.diem:
        parts.append(f"điểm {c.diem}")
    return f"{', '.join(parts)} — NĐ {c.nghi_dinh}"


def aggregate(rules: List[Rule], pick: Optional[str] = None) -> KetQua:
    res = KetQua()
    for r in rules:
        tien = _tien_cua(r, pick)
        tuoc = r.ket_luan.phat_bo_sung.tuoc_gplx_thang
        tru_diem = r.ket_luan.phat_bo_sung.tru_diem
        bs_parts = []
        if tuoc:
            bs_parts.append(f"tước GPLX {tuoc[1]} tháng")
        if tru_diem:
            bs_parts.append(f"trừ {tru_diem} điểm")
        bs = " · ".join(bs_parts) if bs_parts else "—"
        res.chi_tiet.append(DongPhat(r.ket_luan.hanh_vi, tien, _can_cu_str(r), bs))
        res.tong_tien += tien
        if tuoc:
            res.tuoc_gplx_thang_max = max(res.tuoc_gplx_thang_max or 0, tuoc[1])
        if tru_diem:
            res.tru_diem_max = max(res.tru_diem_max or 0, tru_diem)
    return res
