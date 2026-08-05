from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class CanCu(BaseModel):
    nghi_dinh: str
    dieu: int
    khoan: Optional[int] = None
    diem: Optional[str] = None


class PhatBoSung(BaseModel):
    tuoc_gplx_thang: Optional[List[int]] = None  # [min, max] tháng
    tru_diem: Optional[int] = None
    tam_giu_xe_ngay: Optional[int] = None


class KetLuan(BaseModel):
    hanh_vi: str
    tien_phat_min: int
    tien_phat_max: int
    phat_bo_sung: PhatBoSung = Field(default_factory=PhatBoSung)
    can_cu: CanCu


class Rule(BaseModel):
    id: str
    nhom: str
    ap_dung_loai_xe: List[str] = Field(default_factory=list)
    dieu_kien: List[Union[str, Dict[str, Any]]] = Field(default_factory=list)
    ket_luan: KetLuan
    giai_thich_mau: Optional[str] = None


class MetaRule(BaseModel):
    id: str
    loai: str  # "tinh_tiet"
    # Cùng cú pháp điều kiện với Rule: chuỗi lá hoặc node lồng {any|all: [...]}
    dieu_kien: List[Union[str, Dict[str, Any]]] = Field(default_factory=list)
    chon_muc: Optional[str] = None  # "max" (tăng nặng) | "min" (giảm nhẹ)
    # Nhóm hành vi mà tình tiết này điều chỉnh; rỗng = áp cho mọi lỗi.
    ap_dung_nhom: List[str] = Field(default_factory=list)
    ghi_chu: Optional[str] = None

    def ap_dung_cho(self, nhom: str) -> bool:
        return not self.ap_dung_nhom or nhom in self.ap_dung_nhom
