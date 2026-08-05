"""Mẫu bài toán (Mp, Goal, Sol) — theo mô hình COKB / mạng tính toán.

Mỗi mẫu mô tả một *dạng* bài toán suy luận pháp lý:
  - Mp   : giả thiết mẫu (các thuộc tính đối tượng cần có trong đề);
  - Goal : mục tiêu cần tìm;
  - Sol  : lời giải mẫu (chuỗi bước suy diễn chuẩn cho dạng đó).
Khi một tình huống (facts) khớp Mp, hệ biết ngay khung lời giải áp dụng —
đây là tri thức "bài toán mẫu" mà engine dùng để định hướng suy diễn.
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
        return all(bool(group & keys) for group in self.mp_any)

    def specificity(self) -> int:
        return len(self.mp) + len(self.mp_any)


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
        mp_any=[{"chiso.nongDoCon_khiTho", "chiso.nongDoCon_mau"}],
        goal="Xác định mức phạt do vi phạm nồng độ cồn",
        sol=[
            "Deduce_Rules: đối chiếu mức cồn (khí thở/máu) trong nhóm 'nong_do_con'",
            "Meta-rule: áp mức nặng nhất nếu gây tai nạn",
            "Aggregate: gộp tiền phạt, tước GPLX, trừ điểm",
        ],
    ),
    SampleProblem(
        name="An toàn & tín hiệu",
        mp={"phuongtien.loai"},
        goal="Xác định phạt lỗi mũ/dây an toàn/đèn đỏ/giấy tờ",
        sol=[
            "Deduce_Rules: đối chiếu các hành vi bool trong nhóm 'an_toan_tin_hieu'",
            "Aggregate: gộp các lỗi độc lập",
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
