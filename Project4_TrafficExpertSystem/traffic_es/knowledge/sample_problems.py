"""Mẫu bài toán (Mp, Goal, Sol) — theo mô hình COKB / mạng tính toán.

Mỗi mẫu mô tả một *dạng* bài toán suy luận pháp lý:
  - Mp   : giả thiết mẫu (các thuộc tính đối tượng cần có trong đề);
  - Goal : mục tiêu cần tìm;
  - Sol  : lời giải mẫu (chuỗi bước suy diễn chuẩn cho dạng đó).
Khi một tình huống (facts) khớp Mp, hệ biết ngay khung lời giải áp dụng —
đây là tri thức "bài toán mẫu" mà engine dùng để định hướng suy diễn.

Một câu hỏi có thể khớp *nhiều* mẫu (đa lỗi). UI nên hiển thị tất cả
`match_problems(facts)`, không chỉ `best_problem`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class SampleProblem:
    name: str
    mp: Set[str]                    # thuộc tính bắt buộc phải có
    goal: str                       # mục tiêu
    sol: List[str]                  # các bước lời giải mẫu
    mp_any: List[Set[str]] = field(default_factory=list)  # mỗi nhóm cần ≥1

    def matches(self, facts: Dict[str, object]) -> bool:
        keys = set(facts.keys())
        if not self.mp <= keys:
            return False
        if not self.mp_any:
            return bool(self.mp)  # chỉ khớp khi có Mp cụ thể
        return all(bool(group & keys) for group in self.mp_any)

    def specificity(self) -> int:
        return len(self.mp) + sum(len(g) for g in self.mp_any)


# Nhóm hành vi theo file luật — dùng cho mp_any để không khớp “mọi câu có loại xe”.
_AN_TOAN = {
    "hanhvi.vuot_den_do",
    "hanhvi.vuot_den_vang",
    "hanhvi.khong_chap_hanh_csgt",
    "hanhvi.cam_dien_thoai",
    "hanhvi.su_dung_thiet_bi_am_thanh",
    "nguoi.khong_mu_bao_hiem",
    "nguoi.khong_day_an_toan",
}
_LAN_DUONG = {
    "hanhvi.sai_lan",
    "hanhvi.di_nguoc_chieu",
    "hanhvi.quay_dau_cam",
    "hanhvi.dung_do_sai_quy_dinh",
}
_GIAY_TO = {
    "nguoi.khong_gplx",
    "nguoi.gplx_het_han",
    "nguoi.sai_hang_gplx",
    "phuongtien.khong_dang_ky",
    "phuongtien.khong_bao_hiem",
    "phuongtien.khong_dang_kiem",
}
_CHU_XE = {
    "hanhvi.thay_doi_may_khung",
    "hanhvi.thay_doi_bien_so",
    "hanhvi.xe_qua_han_su_dung",
}
_NONG_DO = {"chiso.nongDoCon_khiTho", "chiso.nongDoCon_mau", "clarify.pending_nong_do_con"}


SAMPLE_PROBLEMS: List[SampleProblem] = [
    SampleProblem(
        name="Vi phạm tốc độ",
        mp={"phuongtien.loai", "chiso.tocDo", "chiso.tocDoGioiHan"},
        goal="Xác định mức phạt do vượt tốc độ cho phép",
        sol=[
            "Deduce_Objects (A*): chiso.vuot_toc_do_kmh = tocDo − tocDoGioiHan",
            "Deduce_Rules: đối chiếu ngưỡng vượt trong nhóm luật 'toc_do'",
            "Meta-rule: áp tăng nặng nếu gây tai nạn / tái phạm",
            "Aggregate: gộp tiền phạt, tước GPLX, trừ điểm",
        ],
    ),
    SampleProblem(
        name="Vi phạm tốc độ (suy giới hạn theo khu vực)",
        mp={"phuongtien.loai", "chiso.tocDo", "boicanh.khuVuc"},
        goal="Suy tocDoGioiHan từ khu vực rồi xác định mức phạt vượt tốc độ",
        sol=[
            "Deduce_Objects: chiso.tocDoGioiHan ← boicanh.khuVuc (Func gioi_han_theo_khu_vuc)",
            "Deduce_Objects (A*): chiso.vuot_toc_do_kmh = tocDo − tocDoGioiHan",
            "Deduce_Rules: đối chiếu ngưỡng vượt trong nhóm luật 'toc_do'",
            "Aggregate: gộp tiền phạt",
        ],
    ),
    SampleProblem(
        name="Nồng độ cồn",
        mp={"phuongtien.loai"},
        mp_any=[_NONG_DO],
        goal="Xác định mức phạt do vi phạm nồng độ cồn",
        sol=[
            "Deduce_Rules: đối chiếu mức cồn (khí thở/máu) trong nhóm 'nong_do_con'",
            "Meta-rule: áp mức nặng nhất nếu gây tai nạn",
            "Aggregate: gộp tiền phạt, tước GPLX, trừ điểm",
        ],
    ),
    SampleProblem(
        name="An toàn & tín hiệu",
        mp=set(),
        mp_any=[_AN_TOAN],
        goal="Xác định phạt lỗi mũ bảo hiểm / dây an toàn / đèn đỏ-vàng / không chấp hành CSGT",
        sol=[
            "Deduce_Rules: đối chiếu hành vi trong nhóm 'an_toan_tin_hieu'",
            "Aggregate: gộp các lỗi độc lập theo loại phương tiện",
        ],
    ),
    SampleProblem(
        name="Làn đường & dừng đỗ",
        mp=set(),
        mp_any=[_LAN_DUONG],
        goal="Xác định phạt đi sai làn / ngược chiều / quay đầu cấm / dừng đỗ sai",
        sol=[
            "Deduce_Rules: nhóm 'lan_duong' / 'dung_do'",
            "Aggregate: gộp tiền phạt theo loại phương tiện",
        ],
    ),
    SampleProblem(
        name="Giấy tờ xe / người lái",
        mp=set(),
        mp_any=[_GIAY_TO],
        goal="Xác định phạt thiếu/sai GPLX, đăng ký, bảo hiểm, đăng kiểm",
        sol=[
            "Deduce_Rules: nhóm 'giay_to'",
            "Aggregate: gộp các lỗi giấy tờ độc lập",
        ],
    ),
    SampleProblem(
        name="Chủ xe / cải tạo & biển số",
        mp=set(),
        mp_any=[_CHU_XE],
        goal="Xác định phạt thay đổi số máy/khung, biển số, xe quá hạn sử dụng",
        sol=[
            "Deduce_Rules: nhóm 'chu_xe' / 'bien_so'",
            "Aggregate: mức phạt theo loại phương tiện",
        ],
    ),
]


def match_problems(facts: Dict[str, object]) -> List[SampleProblem]:
    """Các mẫu khớp, sắp theo độ đặc hiệu giảm dần (mẫu cụ thể nhất trước)."""
    matched = [p for p in SAMPLE_PROBLEMS if p.matches(facts)]
    return sorted(matched, key=lambda p: p.specificity(), reverse=True)


def best_problem(facts: Dict[str, object]) -> Optional[SampleProblem]:
    matched = match_problems(facts)
    return matched[0] if matched else None
