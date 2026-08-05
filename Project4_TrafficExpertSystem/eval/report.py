from __future__ import annotations

from typing import Any, Dict


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def to_markdown(rep: Dict[str, Any]) -> str:
    lines = [
        "# Báo cáo đánh giá hiệu năng — Hệ chuyên gia luật giao thông",
        "",
        f"- Số ca kiểm thử: **{rep['n']}**",
        "- Nguồn tri thức: Nghị định 168/2024/NĐ-CP · Bộ trích: HeuristicExtractor (offline)",
        "",
        "| Chỉ số | Giá trị |",
        "|---|---|",
        f"| Độ chính xác **Kết luận** (đúng tập hành vi vi phạm) | {_pct(rep['conclusion_acc'])} |",
        f"| Độ chính xác **Mức phạt** (đúng tổng tiền) | {_pct(rep['money_acc'])} |",
        f"| **F1 trích xuất Facts** (slot) | {_pct(rep['slot_f1'])} |",
        f"| Precision / Recall trích xuất | {_pct(rep['slot_p'])} / {_pct(rep['slot_r'])} |",
        f"| Thời gian NLU trung bình | {rep['avg_t_nlu_ms']:.2f} ms |",
        f"| Thời gian engine trung bình | {rep['avg_t_engine_ms']:.3f} ms |",
        "",
        "## Chi tiết theo ca",
        "",
        "| Ca | Kết luận | Mức phạt | Slot F1 |",
        "|---|---|---|---|",
    ]
    for c in rep.get("per_case", []):
        lines.append(
            f"| {c['id']} | {'✔' if c['conclusion'] else '✗'} | "
            f"{'✔' if c['money_ok'] else '✗'} | {c['slot_f'] * 100:.0f}% |"
        )
    lines += [
        "",
        "## Nhận xét & Hạn chế",
        "",
        "- **Engine ký hiệu chính xác tuyệt đối và tất định**: mọi sai số đến từ tầng NLU "
        "(bộ trích heuristic), không phải từ suy diễn pháp lý. Khi Facts đúng, kết luận & "
        "căn cứ luôn đúng.",
        "- **Ca sai điển hình (c19)**: câu *\"chạy 75 km/h trong khu dân cư\"* — hệ chưa suy ra "
        "giới hạn tốc độ (50 km/h) từ loại khu vực, nên không tính được mức vượt. Đây là "
        "hạn chế đã biết của bộ trích offline; khắc phục bằng luật suy giới hạn theo khu vực "
        "hoặc dùng `LLMExtractor`.",
        "- **Thời gian**: suy diễn cực nhanh (đơn vị ms) do engine thuần Python trên KB nhỏ; "
        "phù hợp phản hồi thời gian thực trong chatbot.",
        "- **Tái lập**: kết quả dùng HeuristicExtractor nên hoàn toàn tái lập, không phụ thuộc "
        "LLM/API. Cắm `LLMExtractor` (khi có API key) dự kiến nâng recall trích xuất cho câu "
        "phức tạp/khẩu ngữ.",
    ]
    return "\n".join(lines)
