# Báo cáo đánh giá hiệu năng — Hệ chuyên gia luật giao thông

- Số ca kiểm thử: **19**
- Nguồn tri thức: Nghị định 168/2024/NĐ-CP · Bộ trích: HeuristicExtractor (offline)

| Chỉ số | Giá trị |
|---|---|
| Độ chính xác **Kết luận** (đúng tập hành vi vi phạm) | 94.7% |
| Độ chính xác **Mức phạt** (đúng tổng tiền) | 94.7% |
| **F1 trích xuất Facts** (slot) | 99.2% |
| Precision / Recall trích xuất | 100.0% / 98.7% |
| Thời gian NLU trung bình | 0.07 ms |
| Thời gian engine trung bình | 0.145 ms |

## Chi tiết theo ca

| Ca | Kết luận | Mức phạt | Slot F1 |
|---|---|---|---|
| c01 | ✔ | ✔ | 100% |
| c02 | ✔ | ✔ | 100% |
| c03 | ✔ | ✔ | 100% |
| c04 | ✔ | ✔ | 100% |
| c05 | ✔ | ✔ | 100% |
| c06 | ✔ | ✔ | 100% |
| c07 | ✔ | ✔ | 100% |
| c08 | ✔ | ✔ | 100% |
| c09 | ✔ | ✔ | 100% |
| c10 | ✔ | ✔ | 100% |
| c11 | ✔ | ✔ | 100% |
| c12 | ✔ | ✔ | 100% |
| c13 | ✔ | ✔ | 100% |
| c14 | ✔ | ✔ | 100% |
| c15 | ✔ | ✔ | 100% |
| c16 | ✔ | ✔ | 100% |
| c17 | ✔ | ✔ | 100% |
| c18 | ✔ | ✔ | 100% |
| c19 | ✗ | ✗ | 86% |

## Nhận xét & Hạn chế

- **Engine ký hiệu chính xác tuyệt đối và tất định**: mọi sai số đến từ tầng NLU (bộ trích heuristic), không phải từ suy diễn pháp lý. Khi Facts đúng, kết luận & căn cứ luôn đúng.
- **Ca sai điển hình (c19)**: câu *"chạy 75 km/h trong khu dân cư"* — hệ chưa suy ra giới hạn tốc độ (50 km/h) từ loại khu vực, nên không tính được mức vượt. Đây là hạn chế đã biết của bộ trích offline; khắc phục bằng luật suy giới hạn theo khu vực hoặc dùng `LLMExtractor`.
- **Thời gian**: suy diễn cực nhanh (đơn vị ms) do engine thuần Python trên KB nhỏ; phù hợp phản hồi thời gian thực trong chatbot.
- **Tái lập**: kết quả dùng HeuristicExtractor nên hoàn toàn tái lập, không phụ thuộc LLM/API. Cắm `LLMExtractor` (khi có API key) dự kiến nâng recall trích xuất cho câu phức tạp/khẩu ngữ.