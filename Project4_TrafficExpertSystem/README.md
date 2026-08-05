# Traffic Expert System

Hệ thống chuyên gia tư vấn xử phạt vi phạm giao thông theo **Nghị định 168/2024/NĐ-CP**.

Người dùng mô tả tình huống bằng tiếng Việt → NLU trích facts → suy diễn luật → trả mức phạt, căn cứ pháp lý và chuỗi giải thích. Giao diện: Streamlit.

## Yêu cầu

- Python 3.10+ (khuyến nghị 3.12)
- API key OpenAI / Anthropic (tùy chọn — không có thì dùng **Heuristic offline**)

## Cài đặt

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

Dùng môi trường `venv` vừa tạo (tránh nhầm `.venv` cũ thiếu package).

## Cấu hình

```bash
cp .env.example .env
```

Chỉnh `.env` (đã gitignore — **không commit key thật**):

```env
# Chọn 1 provider (ưu tiên Anthropic nếu cả hai đều có)
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...

# Tùy chọn
# TRAFFIC_ES_LLM_PROVIDER=openai          # anthropic | openai | local
# TRAFFIC_ES_LLM_MODEL=gpt-4o-mini

# LLM local (Colab / vLLM / Ollama…)
# TRAFFIC_ES_LLM_PROVIDER=local
# TRAFFIC_ES_LOCAL_BASE_URL=https://xxx.trycloudflare.com/v1
# TRAFFIC_ES_LOCAL_MODEL=Qwen/Qwen2.5-Coder-7B-Instruct
```

## Chạy ứng dụng

### Local (venv)

```bash
source venv/bin/activate
streamlit run app/streamlit_app.py
```

Mở [http://localhost:8501](http://localhost:8501).

> Không chạy bằng `python app/streamlit_app.py` — phải dùng `streamlit run`.

### Docker Compose

```bash
cp .env.example .env   # nếu chưa có; điền key nếu cần LLM
docker compose up --build
```

App: [http://localhost:8501](http://localhost:8501). Dừng: `docker compose down`.

Sidebar chọn bộ trích xuất: **Tự động** (theo `.env`), OpenAI, Anthropic, Local, hoặc Heuristic.

## Cách dùng nhanh

1. Nhập mô tả tình huống (vd. *“Tôi lái xe máy vượt đèn đỏ”*).
2. Bấm **Phân tích**.
3. Nếu thiếu thông tin, hệ thống **hỏi bổ sung** (radio chọn, không cần gõ lại câu):
   - Thiếu loại xe → chọn Ô tô / Xe máy
   - Câu mơ hồ (*“sai luật”*) → chọn loại lỗi
   - Đã lộ chủ đề cồn/tốc độ nhưng chưa có mức (*“uống rượu”*, *“quá tốc độ”*) → chọn **khung mức** (không nhập số tay)
4. Xem mức phạt, căn cứ, facts, trace suy diễn.

### Ví dụ khung tốc độ

- Vượt 10–20 km/h *(ví dụ: cho phép 50 km/h, chạy 65 km/h)*
- Các khung khác: 5 đến dưới 10, trên 20 đến 35, trên 35 km/h

### Ví dụ khung nồng độ cồn

- Mức 1 / 2 / 3 theo ngưỡng khí thở (hoặc máu) của Nghị định 168

## Phạm vi hỗ trợ (KG + luật)

Căn cứ chính: **Nghị định 168/2024/NĐ-CP**. Ontology / keyphrase nằm trong
`traffic_es/knowledge/concepts.yaml`; luật suy diễn trong `traffic_es/knowledge/rules/`;
câu hỏi bổ sung (khung mức UI) trong `traffic_es/knowledge/clarify.yaml`.

### Concept trong Knowledge Graph

| Concept | Nhóm | Fact gắn (nếu có) | Ví dụ cách nói khớp |
|---------|------|-------------------|---------------------|
| Xe ô tô | `phuong_tien` | `phuongtien.loai=o_to` | ô tô, xe hơi, xe con, xe tải… |
| Xe mô tô | `phuong_tien` | `phuongtien.loai=xe_may` | xe máy, mô tô, xe gắn máy… |
| Nồng độ cồn | `nong_do_con` | (cần số đo) | uống rượu, bia, nhậu, say xỉn, thổi nồng độ… |
| Tốc độ | `toc_do` | (cần số km/h) | quá tốc độ, vượt tốc độ, phóng nhanh… |
| Không đội mũ bảo hiểm | `mu_bao_hiem` | `nguoi.khong_mu_bao_hiem` | không đội mũ, quên mũ bảo hiểm… |
| Không thắt dây an toàn | `day_an_toan` | `nguoi.khong_day_an_toan` | không thắt dây, không dây an toàn… |
| Vượt đèn đỏ | `tin_hieu` | `hanhvi.vuot_den_do` | vượt đèn, đèn đỏ, không chấp hành hiệu lệnh đèn… |
| Không có GPLX | `giay_to` | `nguoi.coGPLX=false` | không bằng lái, chưa có bằng… |
| Gây tai nạn | `tinh_tiet` | `tinhtiet.gay_tai_nan` | đâm, va chạm, tông, quẹt… |
| Tái phạm | `tinh_tiet` | `tinhtiet.tai_pham` | tái phạm, vi phạm nhiều lần… |

### Luật xử phạt đang suy diễn được

| Nhóm | Loại xe | Mức / nội dung chính | File luật |
|------|---------|----------------------|-----------|
| Nồng độ cồn | Ô tô, xe máy | 3 mức (≤0,25 / 0,25–0,4 / >0,4 mg/l khí thở hoặc tương đương máu) | `rules/nong_do_con.yaml` |
| Vượt tốc độ | Ô tô | 5 đến dưới 10, 10–20, trên 20 đến 35, trên 35 km/h | `rules/toc_do.yaml` |
| Vượt tốc độ | Xe máy | 5 đến dưới 10, 10–20, trên 20 km/h | `rules/toc_do.yaml` |
| Mũ bảo hiểm | Xe máy | Không đội mũ / đội không đúng quy cách | `rules/an_toan_tin_hieu.yaml` |
| Dây an toàn | Ô tô | Không thắt dây khi chạy | `rules/an_toan_tin_hieu.yaml` |
| Tín hiệu đèn | Ô tô, xe máy | Không chấp hành đèn tín hiệu (vượt đèn đỏ) | `rules/an_toan_tin_hieu.yaml` |
| Giấy tờ | Ô tô, xe máy | Điều khiển xe không có GPLX | `rules/an_toan_tin_hieu.yaml` |
| Tình tiết | (meta) | Tăng nặng / giảm nhẹ (vd. gây tai nạn) | `rules/tinh_tiet.yaml` |

> Chưa cover toàn bộ Nghị định 168 — chỉ các nhóm trên. Thêm lỗi mới: bổ sung concept + keyphrase trong KG, luật trong `rules/`, và (nếu cần hỏi khung) mục trong `clarify.yaml`.

## Kiểm thử

```bash
source venv/bin/activate
pytest
```

## Cấu trúc chính

```
app/streamlit_app.py          # UI Streamlit
traffic_es/
  service.py                  # API trả lời + hỏi bổ sung
  nlu/                        # normalize, extract, KG, clarify
  engine/                     # forward chaining, penalty, A*
  knowledge/
    concepts.yaml             # Legal-Onto / KG keyphrases
    clarify.yaml              # câu hỏi UI (khung mức, hành vi)
    rules/                    # luật YAML
  llm/                        # OpenAI / Anthropic / local
  explain/                    # sinh giải thích
tests/
scripts/
notebooks/colab_qwen_server.ipynb
```

## Ghi chú bảo mật

- Chỉ commit `.env.example` (placeholder). File `.env` và `venv/` / `.venv/` nằm trong `.gitignore`.
- Không dán API key lên README, issue hay PR.
