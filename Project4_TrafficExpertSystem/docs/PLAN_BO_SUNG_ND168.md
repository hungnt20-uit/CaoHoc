# Kế hoạch bổ sung KB — Nghị định 168/2024/NĐ-CP

> Mục tiêu: mở rộng hệ chuyên gia từ **MVP hiện tại** (cồn, tốc độ, mũ/dây, đèn đỏ, không GPLX + tình tiết) sang phủ các nhóm hành vi chính trong NĐ 168.  
> Cập nhật: 2026-08-05

---

## 0. Hiện trạng (baseline)

| Thành phần | Hiện có |
|---|---|
| Legal-Onto | ~10 concept trong `concepts.yaml` |
| Rules | `nong_do_con.yaml`, `toc_do.yaml`, `an_toan_tin_hieu.yaml`, `tinh_tiet.yaml` (~19 rule + meta) |
| Phương tiện | Chỉ `o_to`, `xe_may` — **chưa** xe đạp / xe thô sơ |
| Eval | 19 ca heuristic; c19 fail (chưa suy giới hạn tốc độ theo khu vực) |

**Nguyên tắc bổ sung mỗi lỗi mới:**

1. Thêm **concept + keyphrases** (`concepts.yaml`)
2. Thêm **fact schema** nếu cần (`nlu/grounding.py`)
3. Thêm **rule YAML** + `can_cu` NĐ 168 (Điều/Khoản/điểm, khung tiền, phạt bổ sung)
4. (Tuỳ chọn) **clarify.yaml** nếu cần hỏi khung mức
5. Thêm ca vào `eval/testset.jsonl` + pytest
6. Cập nhật README phạm vi hỗ trợ

---

## 1. Ưu tiên P0 — Vá lỗ hổng MVP (làm trước)

| # | Hạng mục | Việc cần làm | File chính |
|---|---|---|---|
| P0.1 | Suy giới hạn tốc độ theo khu vực | `khu_dan_cu` → `tocDoGioiHan=50` (và các khu khác nếu có trong NĐ/QCVN) | `engine/funcs.py` hoặc rule Func; `deduction_network.py`; fix ca **c19** |
| P0.2 | Đèn vàng / hiệu lệnh CSGT | Tách hoặc mở rộng concept `tin_hieu`; rule riêng nếu mức phạt khác đèn đỏ | `concepts.yaml`, `an_toan_tin_hieu.yaml` |
| P0.3 | Ma túy / chất kích thích | Concept + fact + rules (ô tô/xe máy) theo NĐ 168 | `concepts.yaml`, rule mới `chat_kich_thich.yaml` |
| P0.4 | GPLX: chưa đủ tuổi / không đúng thẩm quyền | Mở rộng nhóm `giay_to` ngoài `coGPLX=false` | `concepts.yaml`, `an_toan_tin_hieu.yaml` hoặc `giay_to.yaml` |

---

## 2. Ưu tiên P1 — Nhóm người điều khiển (còn thiếu)

| # | Chủ đề | Concept / facts gợi ý | Rules |
|---|---|---|---|
| P1.1 | Sai làn / phần đường | `hanhvi.sai_lan`, `hanhvi.sai_phan_duong` | `lan_duong.yaml` |
| P1.2 | Chuyển làn không báo hiệu | `hanhvi.chuyen_lan_khong_tin_hieu` | cùng file trên |
| P1.3 | Quay đầu nơi cấm | `hanhvi.quay_dau_cam` | `quy_tac_tranh_vuot.yaml` |
| P1.4 | Vượt xe nơi cấm vượt | `hanhvi.vuot_cam` | cùng file |
| P1.5 | Đi ngược chiều / đường một chiều | `hanhvi.nguoc_chieu` | cùng file |
| P1.6 | Dừng, đỗ sai quy định / nơi cấm | `hanhvi.dung_do_sai`, `boicanh.vi_tri_cam_do` | `dung_do.yaml` |
| P1.7 | Xe đạp / xe thô sơ | `phuongtien.loai=xe_dap` (+ rules tương ứng nếu NĐ có mức riêng) | concepts + rules liên quan |

---

## 3. Ưu tiên P2 — Giấy tờ, biển số

| # | Chủ đề | Gợi ý |
|---|---|---|
| P2.1 | Biển số giả / che biển / sửa ký hiệu | Concept `bien_so` + rules `bien_so.yaml` |
| P2.2 | Không mang / không có Đăng ký xe | `giayto.dang_ky_xe` |
| P2.3 | Không mang / hết hạn đăng kiểm (ô tô) | `giayto.dang_kiem` |
| P2.4 | Tách file `giay_to.yaml` khỏi `an_toan_tin_hieu.yaml` cho dễ bảo trì | refactor nhẹ |

---

## 4. Ưu tiên P3 — Vận tải đường bộ

| # | Chủ đề | Gợi ý |
|---|---|---|
| P3.1 | Chở quá tải / quá khổ | `van_tai.yaml` — facts khối lượng, khổ giới hạn |
| P3.2 | Nhồi nhét hành khách / quá số người | facts `so_nguoi`, `suc_chua` |
| P3.3 | Thu tiền quá giá vé niêm yết | (ít gặp NL hiện trường — ưu tiên thấp hơn) |
| P3.4 | Đón/trả khách sai nơi / trên cao tốc | `hanhvi.don_tra_khach_sai` |

---

## 5. Ưu tiên P4 — Hành khách, người đi bộ, chủ xe

| # | Chủ đề | Gợi ý |
|---|---|---|
| P4.1 | Hành khách gây rối / đe dọa / đu bám / mở cửa khi xe chạy | `hanh_khach.yaml` |
| P4.2 | Người đi bộ sai phần đường / không chấp hành đèn | `nguoi_di_bo.yaml` |
| P4.3 | Chủ xe giao xe cho người không đủ ĐK | `chu_xe.yaml` |
| P4.4 | Tự ý thay đổi máy / khung / màu sơn | cùng nhóm chủ xe / phương tiện |

---

## 6. Hạ tầng kỹ thuật đi kèm (không phải “điều luật” nhưng cần làm)

| # | Việc | Lý do |
|---|---|---|
| T.1 | Mở rộng `grounding.SCHEMA` cho fact mới | Tránh fact bị loại khi validate |
| T.2 | HeuristicExtractor / LLM prompt closed-vocab | Nhận diện keyphrase / slot mới |
| T.3 | Sample problems (`sample_problems.py`) | Demo Goal/Sol cho lỗi mới |
| T.4 | Eval: thêm ≥3–5 ca / nhóm lỗi mới | Giữ metric minh bạch |
| T.5 | (Tuỳ chọn) Làm giàu quan hệ KG `R_hier` / `R_con` | Slide Legal-Onto đầy đủ hơn star-graph hiện tại |
| T.6 | Eval head-to-head Heuristic vs OpenAI vs Local | Báo cáo NLU công bằng hơn chỉ heuristic |
| T.7 | Cập nhật slide / README phạm vi sau mỗi phase | Tránh overclaim “full NĐ 168” |

---

## 7. Lộ trình đề xuất

| Phase | Thời gian gợi ý | Deliverable |
|---|---|---|
| **Phase A** | Tuần 1 | P0.1–P0.4 xong; c19 pass; ma túy + GPLX mở rộng |
| **Phase B** | Tuần 2–3 | P1 (làn đường, tránh vượt, dừng đỗ); xe đạp nếu cần demo |
| **Phase C** | Tuần 4 | P2 giấy tờ / biển số |
| **Phase D** | Tuần 5+ | P3 vận tải + P4 hành khách/đi bộ/chủ xe; eval mở rộng |

Mỗi phase: **concept → rule → test → README**. Không merge rule thiếu `can_cu` NĐ 168.

---

## 8. Định nghĩa “xong” một nhóm lỗi

- [x] Có concept + keyphrases tiếng Việt thường gặp  
- [x] Có ≥1 rule YAML với LHS/RHS/`can_cu` NĐ 168 (cần đối chiếu văn bản gốc khi audit)  
- [x] Engine fire đúng trên ≥1 câu NL demo (`tests/test_nd168_expansion.py`)  
- [x] Có ca trong `testset.jsonl` (c19–c28)  
- [x] README liệt kê nhóm trong “Phạm vi hỗ trợ”

### Trạng thái triển khai (2026-08-05, nhánh `feature/nd168-kb-expansion`)

| Phase | Hạng mục | Trạng thái |
|---|---|---|
| A / P0 | Giới hạn khu vực, đèn vàng/CSGT, ma túy, GPLX mở rộng | Đã làm |
| B / P1 | Làn đường, tránh vượt, dừng đỗ, xe đạp | Đã làm |
| C / P2 | Biển số, ĐKX/đăng kiểm, tách `giay_to.yaml` | Đã làm |
| D / P3–P4 | Vận tải, hành khách, đi bộ, chủ xe | Đã làm (MVP facts/rules) |

---

## 9. Rủi ro

- Số hóa sai Điều/Khoản/khung tiền → **legal hallucination ở tầng KB** (không phải LLM). Cần đối chiếu văn bản gốc.  
- Trùng / chồng hành vi (một câu nhiều lỗi) — đã có gộp phạt; cần test kỹ khi thêm rule.  
- Overclaim trên slide: chỉ nói “đã cover” các nhóm trong README, không nói “toàn bộ NĐ 168” cho đến Phase D.
